import os
import openai
import dotenv
import pandas as pd
# import Levenshtein
import asyncio
import time
import random
from datetime import datetime, timedelta


dotenv.load_dotenv()

number_of_reviews = 20
rating_left = 1
rating_right = 2
openai.api_key = os.getenv("OPENAI_API_KEY")

body = []
emails = []
names = []

new_reviews = ""
new_emails = ""
new_names = ""
total_tokens = 0

# def check_unique(new_review: str):
#     global body
#     for review in body:
#         distance = Levenshtein.distance(review, new_review)
#         print(distance)


def clean(content: str):
    return content.replace('"', "").strip()


async def read_csv_file():
    global body, emails, names, number_of_reviews

    review = pd.read_csv("data/reviews.csv")
    body = review["body"].to_numpy()
    emails = review["reviewer_email"].head(10).to_numpy()
    names = review["reviewer_name"].head(10).to_numpy()
    examples = ""
    length = len(body)

    for i in range(0, min(10, length)):
        examples += f"Sample Review {i}: \n {str(body[i])}\n\n"
    with open("./data/reviews.txt", "w") as txt_file:
        txt_file.write(examples.strip())

    tasks = []
    number_of_reviews = number_of_reviews / 2
    short = int(number_of_reviews * 0.6)
    medium = int(number_of_reviews * 0.3)
    long = int(number_of_reviews * 0.1)

    for i in range(short):
        tasks.append(create_reviews(
            examples, 25, 75, rating_left, rating_right))
    for i in range(medium):
        tasks.append(create_reviews(
            examples, 75, 130, rating_left, rating_right))
    for i in range(long):
        tasks.append(create_reviews(
            examples, 150, 200, rating_left, rating_right))

    number_of_reviews = (short + medium + long) * 2
    tasks.extend([create_emails(number_of_reviews),
                 create_names(number_of_reviews)])
    await asyncio.gather(*tasks)


async def create_reviews(examples: str, low: int, high: int, rating_left: int, rating_right: int):
    global new_reviews, total_tokens

    instructor = f"""
        You will act as a customer from now on.        
        Each review contains {low}-{high} words.
        You have to write 2 reviews rating of {rating_left}-{rating_right} stars  (mostly {rating_right} stars), so your final output should contain {low*2}-{high*2} words.
        The more stars of product the better.
        Write 2 reviews containing some csv-readable, rare, specific emojis that are appropriate to content of review based on user provided sample reviews.
        
        I hope also some of the reviews to write about how products are good for users.
        Don't forget that each review should contain {low}-{high} words.
        And output only one suitable title in front of review without quotes and don't output any extra header except title of review.
        And this title must start with emoji that is appropriate to title.
        Split title and content of review with "/".
        please split two reviews with character '|'.
    """

    completion = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instructor},
            {"role": "user",
             "content": f"""
                These are sample reviews you can refer to.
                {examples}
                Please create reviews.
                Don't forget to split two reviews with 
             """
             }
        ]
    )
    total_tokens += completion.usage["total_tokens"]
    new_reviews += completion.choices[0].message["content"] + "\n | "
    with open("./data/reviews.txt", "w") as txt_file:
        txt_file.write(completion.choices[0].message["content"])


async def create_emails(num: int):
    global new_emails, emails, total_tokens
    instructor = """
        You will act as a email address generator.
        Based on sample emails provided by users, please generate realistic-looking email addresses without quotes.
        I will not use these emails for illegal purpose.
        Please split all generated emails with character "|".
    """

    completion = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instructor},
            {"role": "user",
             "content": f"""
                These are sample emails you can refer to.
                {emails}
                Please create {num} emails.
             """
             }
        ]
    )
    total_tokens += completion.usage["total_tokens"]
    print(completion.choices[0].message["content"])
    new_emails += completion.choices[0].message["content"]


def regenerate_title(list_titles):
    instructor = """
        Rewrite user provided titles below so that all titles are absolutely different each other.
        All emojis should be absolutely different each other too.
        Split rewritten titles with character "|".
    """

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instructor},
            {"role": "user",
             "content": f"""
                These are titles you should rewrite.
                {list_titles}
                Please output rewritten titles.
             """
             }
        ]
    )
    return completion.choices[0].message["content"]


async def create_names(num: int):
    global new_names, names, total_tokens
    instructor = """
        You will act as a name generator.
        Based on sample names provided by users, please generate realistic-looking names without quotes.
        I will not use these names for illegal purpose.
        Please split all generated names with character "|".
    """

    completion = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instructor},
            {"role": "user",
             "content": f"""
                These are sample names you can refer to.
                {names}
                Please create {num} names.
             """
             }
        ]
    )
    total_tokens += completion.usage["total_tokens"]
    print(completion.choices[0].message["content"])
    new_names += completion.choices[0].message["content"]


def generate_rates(num: int):
    num_left = int(num * 0.1)
    result = [rating_left] * num_left
    result += [rating_right] * (num - num_left)
    random.shuffle(result)
    return result


def generate_dates(num: int, start_date, end_date):
    print(start_date, end_date)
    result = []
    for i in range(num):
        random_number_of_days = random.randrange((end_date - start_date).days)
        result.append(start_date + timedelta(days=random_number_of_days))
    return result


async def start():
    global new_emails, new_names

    current_time = time.time()
    await read_csv_file()

    list_reviews = new_reviews.split("|")
    list_titles = []
    list_bodys = []

    with open("./data/reviews.txt", "w") as txt_file:
        txt_file.write(new_reviews)
        for review in list_reviews:
            titles_and_bodys = review.split("/")
            if len(titles_and_bodys) != 2:
                continue
            list_titles.append(clean(titles_and_bodys[0]))
            list_bodys.append(clean(titles_and_bodys[1]))

    list_emails = clean(new_emails).split('|')
    list_names = clean(new_names).split('|')

    list_titles = regenerate_title(list_titles).split('|')

    print("list_titles: ", len(list_titles))
    print("list_bodys: ", len(list_bodys))

    min_len = min(len(list_titles), len(list_bodys),
                  len(list_names), len(list_emails))
    print(min_len)
    while min_len != number_of_reviews:
        start()

    list_titles = list_titles[:min_len]
    list_bodys = list_bodys[:min_len]
    list_names = list_names[:min_len]
    list_emails = list_emails[:min_len]

    list_rates = generate_rates(min_len)
    list_dates = generate_dates(min_len, str2date(From), str2date(To))

    final_reviews = {
        "title": list_titles,
        "body": list_bodys,
        "rating": list_rates,
        "reply_date": list_dates,
        "reviewer_name": list_names,
        "reviewer_email": list_emails
    }

    result = pd.DataFrame(final_reviews)
    result.to_csv("./data/new_reviews.csv", index=False, encoding='utf-8-sig')
    print("total_tokens: ", total_tokens)
    print(time.time() - current_time)


asyncio.run(start())
