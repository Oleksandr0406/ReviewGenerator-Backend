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
openai.api_key = os.getenv("OPENAI_API_KEY")

body = []
emails = []
names = []
titles = []
keywords_to_focus_on = ""
new_reviews = ""
new_emails = ""
new_names = ""
new_rates = []
total_tokens = 0

# def check_unique(new_review: str):
#     global body
#     for review in body:
#         distance = Levenshtein.distance(review, new_review)
#         print(distance)


def init():
    global new_reviews, new_emails, new_names, total_tokens, new_rates
    new_reviews = ""
    new_emails = ""
    new_names = ""
    new_rates = []
    total_tokens = 0


def clean(content: str):
    return content.replace('"', "").strip()


def str2date(date_str: str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def choose_rate(rate: list):
    percent = sum(rate)
    rand = random.randint(1, percent)
    for i in range(0, 6):
        if rand <= sum(rate[:(i+1)]):
            return i


async def read_csv_file(filename: str, rate: list):
    global body, emails, names, number_of_reviews, new_rates, titles

    review = pd.read_csv(f"data/{filename}")
    titles = review["title"].head(5).to_numpy()
    body = review["body"].to_numpy()
    emails = review["reviewer_email"].head(10).to_numpy()
    names = review["reviewer_name"].head(5).to_numpy()
    examples = ""
    length = len(body)

    for i in range(0, min(5, length)):
        examples += f"Sample Review {i}: \n {str(body[i])}\n\n"
    with open("./data/reviews.txt", "w") as txt_file:
        txt_file.write(examples.strip())

    tasks = []
    number_of_reviews = int(number_of_reviews / 2)
    medium = int(number_of_reviews * 0.3)
    long = int(number_of_reviews * 0.1)
    short = int(number_of_reviews - medium - long)

    for i in range(long):
        current_rate = choose_rate(rate)
        new_rates += [current_rate] * 2
        tasks.append(create_reviews(
            examples, 200, 300, current_rate))
    for i in range(medium):
        current_rate = choose_rate(rate)
        new_rates += [current_rate] * 2
        tasks.append(create_reviews(
            examples, 100, 130, current_rate))
    for i in range(short):
        current_rate = choose_rate(rate)
        new_rates += [current_rate] * 2
        tasks.append(create_reviews(
            examples, 25, 75, current_rate))

    print(short, medium, long)
    number_of_reviews *= 2
    tasks.extend([create_emails(number_of_reviews),
                 create_names(number_of_reviews)])
    await asyncio.gather(*tasks)


async def create_reviews(examples: str, low: int, high: int, current_rate: int):
    global new_reviews, total_tokens
    emoji_prompt = "Then insert suitable emoji at the front of some words of review but that words shouldn't be the last word of any sentences." if random.randint(
        1, 5) == 3 else ""
    print(emoji_prompt)
    instructor = f"""
        Each review contains {low}-{high} words.
        You have to write 2 reviews rating of {current_rate} stars, so your final output should contain {low*2}-{high*2} words.
        1 or 2 rates are bad, 3 is normal, 4 is good and 5 means excellent.
        The more stars of product the better.
        Write 2 reviews based on user provided sample reviews below.
        When you write reviews, you must focus on one of below topics.
        topics: {keywords_to_focus_on}
        {emoji_prompt}
        I hope also some of the reviews to write about how products are good for users.
        And I hope some reivews to have a bit grammer or spell errors like human-written-reviews.
        Don't forget that each review should contain {low}-{high} words.
        And output only one suitable title in front of review without quotes and don't output any extra header except title of review.
        Split title and content of each review with "/" like sample format.
        Please split two reviews with character '|'.
        ----------------
        Sample Format(don't output this line)
        A Magical Change /
        I was looking for something to ✨ boost the color of my hair.
        | (This is character that is split reviews. Remember this!)
        Hydrated colored hair /
        Very easy to use, it lathers very quickly.
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
                Don't forget to split two reviews with character '|'.
             """
             }
        ]
    )
    total_tokens += completion.usage["total_tokens"]
    new_reviews += completion.choices[0].message["content"] + "\n |"
    with open("./data/reviews.txt", "w") as txt_file:
        txt_file.write(completion.choices[0].message["content"])


async def create_emails(num: int):
    global new_emails, emails, total_tokens
    instructor = """
        You will act as a email address generator.
        Based on sample emails provided by users, please generate realistic-looking email addresses without "'".
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
    # print(completion.choices[0].message["content"])
    new_emails += completion.choices[0].message["content"]


def regenerate_title(len, list_titles):
    emoji_prompt = f"Then insert suitable emojis at the front of some words of title for only {len/5} titles but that words shouldn't be the first or last word of any title."
    sample_title = '\n'.join(str(title) for title in titles)
    print(sample_title)
    instructor = f"""
        These are titles you can refer to that is very similar to human-written.
        {sample_title}
        Based on above title samples, rewrite {len} of user provided titles below so that all titles are completely different each other.
        {emoji_prompt}
        Split generated titles with character "|".
        -------
        Sample Format
        Elevate ✨Your Hue | Elevate Your Hue
    """
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instructor},
            {"role": "user",
             "content": f"""
                These are {len} of titles you should rewrite.
                {list_titles}
                Please generate {len} titles completely different each other based on above list.
                {emoji_prompt}
                Don't forget to split generated titles with character "|".
             """
             }
        ]
    )
    # print(completion.choices[0].message["content"])
    return completion.choices[0].message["content"]


async def create_names(num: int):
    global new_names, names, total_tokens
    instructor = """
        You will act as a name generator.
        Based on sample names provided by users, please generate realistic-looking names without "'".
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
    # print(completion.choices[0].message["content"])
    new_names += completion.choices[0].message["content"]


def generate_dates(num: int, start_date, end_date):
    result = []
    for i in range(num):
        random_number_of_days = random.randrange((end_date - start_date).days)
        result.append(
            (start_date + timedelta(random_number_of_days)).strftime("%Y-%m-%d"))
    return result


async def start(reviewCount: int, rate: int, From: str, To: str, keywords: str, filename: str):
    global new_emails, new_names, number_of_reviews, rating_right, keywords_to_focus_on
    number_of_reviews = reviewCount
    keywords_to_focus_on = keywords
    current_time = time.time()
    init()
    await read_csv_file(filename, rate)

    list_reviews = new_reviews.split("|")
    list_titles = []
    list_bodys = []

    with open("./data/reviews.txt", "w") as txt_file:
        txt_file.write(new_reviews)
    for review in list_reviews:
        titles_and_bodys = review.split("/")
        if len(titles_and_bodys) < 2:
            continue
        # print(clean(titles_and_bodys[0]),
        #       "-----", clean(titles_and_bodys[1]))
        list_titles.append(clean(titles_and_bodys[0]))
        list_bodys.append(clean(titles_and_bodys[1]))

    list_emails = clean(new_emails).split('|')
    list_names = clean(new_names).split('|')
    # print(len(list_emails))
    # print(len(list_names))
    list_titles = regenerate_title(
        len(list_titles), '\n'.join(list_titles)).split('|')

    print("list_titles: ", len(list_titles))
    print("list_bodys: ", len(list_bodys))

    min_len = min(len(list_titles), len(list_bodys),
                  len(list_names), len(list_emails))
    print(min_len)

    list_titles = list_titles[:min_len]
    list_bodys = list_bodys[:min_len]
    list_names = list_names[:min_len]
    list_emails = list_emails[:min_len]
    list_rates = new_rates[:min_len]
    list_dates = generate_dates(min_len, str2date(From), str2date(To))

    reveiws_to_return = []
    for i in range(min_len):
        reveiws_to_return.append({"title": list_titles[i], "body": list_bodys[i], "reviewRating": list_rates[i],
                                 "date": list_dates[i], "reviewerName": list_names[i].replace("'", ""), "reviewerEmail": list_emails[i].replace("'", "")})

    print("total_tokens: ", total_tokens)
    print(time.time() - current_time)

    return reveiws_to_return