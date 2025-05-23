import gspread
from collections import Counter
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- SETUP ---
SERVICE_ACCOUNT_FILE = 'credentials/gspread_creds.json'  # Update if needed
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SPREADSHEET_ID = '1Q-lsu_gVuiTFbJw4MlhmjMIjieRDvonkRePYVBICRRE'  # Replace with your sheet ID
NEW_SHEET_NAME = "Sentiment Analysis"


def authorize_clients():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    gspread_client = gspread.authorize(creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    return gspread_client, sheets_service, creds


def get_or_create_sentiment_sheet(gspread_client):
    spreadsheet = gspread_client.open_by_key(SPREADSHEET_ID)
    try:
        worksheet = spreadsheet.worksheet(NEW_SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=NEW_SHEET_NAME, rows=10, cols=10)
    return worksheet


def update_sentiment_counts(worksheet, original_worksheet):
    sentiments = original_worksheet.col_values(4)[1:]  # Column D (skip header)
    counts = Counter(sentiments)

    labels = ["Positive", "Neutral", "Negative"]
    values = [counts.get(label, 0) for label in labels]

    # Ensure at least 8 columns
    if worksheet.col_count < 8:
        worksheet.add_cols(8 - worksheet.col_count)

    # Write sentiment table to G1:H4
    worksheet.update(range_name="G1", values=[["Sentiment", "Count"]])
    worksheet.update(range_name="G2:G4", values=[[label] for label in labels])
    worksheet.update(range_name="H2:H4", values=[[value] for value in values])
    print("✅ Sentiment counts written to 'Sentiment Analysis' sheet.")


def create_sentiment_chart(sheet_service, sheet_id):
    requests = [
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Sentiment Distribution",
                        "pieChart": {
                            "legendPosition": "RIGHT_LEGEND",
                            "threeDimensional": False,
                            "domain": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": sheet_id,
                                        "startRowIndex": 1,
                                        "endRowIndex": 4,
                                        "startColumnIndex": 6,  # Column G
                                        "endColumnIndex": 7
                                    }]
                                }
                            },
                            "series": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": sheet_id,
                                        "startRowIndex": 1,
                                        "endRowIndex": 4,
                                        "startColumnIndex": 7,  # Column H
                                        "endColumnIndex": 8
                                    }]
                                }
                            }
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": sheet_id,
                                "rowIndex": 0,
                                "columnIndex": 9
                            },
                            "offsetXPixels": 20,
                            "offsetYPixels": 20
                        }
                    }
                }
            }
        }
    ]

    body = {"requests": requests}
    sheet_service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=body
    ).execute()
    print("✅ Sentiment pie chart added to 'Sentiment Analysis' sheet.")


def main():
    gspread_client, sheet_service, creds = authorize_clients()

    # Get original worksheet (first sheet)
    original_ws = gspread_client.open_by_key(SPREADSHEET_ID).sheet1

    # Create or get Sentiment Analysis sheet
    sentiment_ws = get_or_create_sentiment_sheet(gspread_client)
    sentiment_sheet_id = sentiment_ws._properties['sheetId']

    # Update sentiment count data
    update_sentiment_counts(sentiment_ws, original_ws)

    # Add the pie chart
    create_sentiment_chart(sheet_service, sentiment_sheet_id)


if __name__ == "__main__":
    main()
