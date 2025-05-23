import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cohere
import os
from dotenv import load_dotenv
import time

# Load .env if used
load_dotenv()

# === Setup ===
CREDENTIALS_FILE = "credentials/gspread_creds.json"
SHEET_NAME = "Redmi 6 Reviews"
WORKSHEET_NAME = "Sheet1"

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(COHERE_API_KEY)

# === Connect to Google Sheet ===
def connect_to_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

# === Analyze review with Cohere ===
def analyze_review(text):
    # Sentiment classification
    sentiment_prompt = f"Classify the sentiment of this review as Positive, Negative, or Neutral:\n{text}\nSentiment:"
    sentiment_response = co.generate(
        model='command',
        prompt=sentiment_prompt,
        max_tokens=1,
        temperature=0.3,
    )
    sentiment = sentiment_response.generations[0].text.strip()

    # Short summary generation using custom prompt
    if len(text) > 50:
        summary_prompt = f"Summarize this review in one short sentence:\n{text}\nShort Summary:"
        summary_response = co.generate(
            model='command',
            prompt=summary_prompt,
            max_tokens=50,
            temperature=0.5,
        )
        summary = summary_response.generations[0].text.strip()
    else:
        summary = text.strip()  # Short enough already

    # Action flag
    action = "Yes" if sentiment.lower() == "negative" else "No"

    return sentiment, summary, action


# === Main Execution ===
def process_reviews():
    worksheet = connect_to_sheet()
    rows = worksheet.get_all_values()

    header = rows[0]
    reviews = rows[1:]  # Skip header row

    # Ensure headers D, E, F exist
    if len(header) < 6:
        header += [""] * (6 - len(header))
    header[3] = "AI Sentiment"
    header[4] = "AI Summary"
    header[5] = "Action Needed?"
    worksheet.update(values=[header], range_name="A1:F1")

    # Loop through each review
    for i, row in enumerate(reviews, start=2):  # Row numbers start at 2
        if len(row) < 3 or not row[2].strip():
            continue  # Skip rows with no review in column C

        review = row[2]
        sentiment, summary, action = analyze_review(review)

        worksheet.update(range_name=f"D{i}", values=[[sentiment]])
        worksheet.update(range_name=f"E{i}", values=[[summary]])
        worksheet.update(range_name=f"F{i}", values=[[action]])

        time.sleep(1)  # Respect API rate limits

    print("✅ Reviews analyzed and updated.")

# === Run Script ===
if __name__ == "__main__":
    process_reviews()
