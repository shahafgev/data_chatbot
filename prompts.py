import streamlit as st
import os
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1zMDhsBkM6lb2yci3vqeoS--Vsz2-SryFnYP3I_dDqI4"
RANGE_NAME = "Sheet1!A:AC"  # Data starts from column A and AC


QUALIFIED_TABLE_NAME = "Sheet1"
TABLE_DESCRIPTION = """

This view contains various statistics for NBA players during the 2021-2022 season, representing averages per game.
The statistics include player positions, team affiliations, games played, minutes played, field goals, three-pointers,
free throws, rebounds, assists, steals, blocks, turnovers, personal fouls, and points.
"""

GEN_SQL = """
You will be acting as an AI Snowflake SQL expert named Dan.
Your goal is to give correct, executable SQL queries to users.
You will be replying to users who will be confused if you don't respond in the character of Dan.
You are given one table, the table name is in <tableName> tag, the columns are in <columns> tag.
The user will ask questions; for each question, you should respond and include a SQL query based on the question and the table. 

{context}

Here are 7 critical rules for the interaction you must abide:
<rules>
1. You MUST wrap the generated SQL queries within ``` sql code markdown in this format e.g
```sql
(select 1) union (select 2)
```
2. If I don't tell you to find a limited set of results in the sql query or question, you MUST limit the number of responses to 10.
3. Text / string where clauses must be fuzzy match e.g ilike %keyword%
4. Make sure to generate a single Snowflake SQL code snippet, not multiple. 
5. You should only use the table columns given in <columns>, and the table given in <tableName>, you MUST NOT hallucinate about the table names.
6. DO NOT put numerical at the very front of SQL variable.
</rules>
7. YOU SHOULD ALWAYS WRAP THE COLUMNS NAMES WITH "" WHEN WRITING A QUERY

Don't forget to use "ilike %keyword%" for fuzzy match queries (especially for variable_name column)
and wrap the generated sql code with ``` sql code markdown in this format e.g:
```sql
(select 1) union (select 2)
```

For each question from the user, make sure to include a query in your response.

Now to get started, please briefly introduce yourself, describe the table at a high level, and share the available metrics in 2-3 sentences.
Then provide 3 example questions using bullet points.
"""


def get_table_from_sheet():
    credentials = None
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file("token.json")
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            credentials = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(credentials.to_json())
    try:
        service = build("sheets", "v4", credentials=credentials)
        sheets = service.spreadsheets()
        result = sheets.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get("values", [])
        if values:
            QA_df = pd.DataFrame(values[1:], columns=values[0])  # Assuming the first row contains headers
            return QA_df
        else:
            print("No data found in the sheet.")
    except HttpError as error:
        print(error)



def get_table_context(table_name: str, table_description: str, rows):
    # Extract column names from the first row of the Google Sheet data
    header_row = rows[0]
    column_names = header_row

    # Generate a dictionary of column descriptions (assuming you have these in a separate sheet)
    column_descriptions = {
        "PLAYER": "The player name",
        "POS": "Player position (C = center, PF = power forward, SF = small forward, SG = shooting guard, PG = point guard)",
        "TM": "Team affiliation, "
              """   ATL: Atlanta Hawks - City: Atlanta, State: Georgia, Conference: Eastern Conference
                    BOS: Boston Celtics - City: Boston, State: Massachusetts, Conference: Eastern Conference
                    BRK: Brooklyn Nets - City: Brooklyn, State: New York, Conference: Eastern Conference
                    CHA: Charlotte Hornets - City: Charlotte, State: North Carolina, Conference: Eastern Conference
                    CHI: Chicago Bulls - City: Chicago, State: Illinois, Conference: Eastern Conference
                    CLE: Cleveland Cavaliers - City: Cleveland, State: Ohio, Conference: Eastern Conference
                    DAL: Dallas Mavericks - City: Dallas, State: Texas, Conference: Western Conference
                    DEN: Denver Nuggets - City: Denver, State: Colorado, Conference: Western Conference
                    DET: Detroit Pistons - City: Detroit, State: Michigan, Conference: Eastern Conference
                    GSW: Golden State Warriors - City: San Francisco, State: California, Conference: Western Conference
                    HOU: Houston Rockets - City: Houston, State: Texas, Conference: Western Conference
                    IND: Indiana Pacers - City: Indianapolis, State: Indiana, Conference: Eastern Conference
                    LAC: LA Clippers - City: Los Angeles, State: California, Conference: Western Conference
                    LAL: Los Angeles Lakers - City: Los Angeles, State: California, Conference: Western Conference
                    MEM: Memphis Grizzlies - City: Memphis, State: Tennessee, Conference: Western Conference
                    MIA: Miami Heat - City: Miami, State: Florida, Conference: Eastern Conference
                    MIL: Milwaukee Bucks - City: Milwaukee, State: Wisconsin, Conference: Eastern Conference
                    MIN: Minnesota Timberwolves - City: Minneapolis, State: Minnesota, Conference: Western Conference
                    NOP: New Orleans Pelicans - City: New Orleans, State: Louisiana, Conference: Western Conference
                    NYK: New York Knicks - City: New York City, State: New York, Conference: Eastern Conference
                    OKC: Oklahoma City Thunder - City: Oklahoma City, State: Oklahoma, Conference: Western Conference
                    ORL: Orlando Magic - City: Orlando, State: Florida, Conference: Eastern Conference
                    PHI: Philadelphia 76ers - City: Philadelphia, State: Pennsylvania, Conference: Eastern Conference
                    PHO: Phoenix Suns - City: Phoenix, State: Arizona, Conference: Western Conference
                    POR: Portland Trail Blazers - City: Portland, State: Oregon, Conference: Western Conference
                    SAC: Sacramento Kings - City: Sacramento, State: California, Conference: Western Conference
                    SAS: San Antonio Spurs - City: San Antonio, State: Texas, Conference: Western Conference
                    TOR: Toronto Raptors - City: Toronto, Province: Ontario, Conference: Eastern Conference
                    UTA: Utah Jazz - City: Salt Lake City, State: Utah, Conference: Western Conference
                    WAS: Washington Wizards - City: Washington, D.C., Conference: Eastern Conference """,
        "AGE": "The player's age",
        "G": "Games played",
        "GS": "Games started",
        "MP": "Minutes played",
        "FG": "Field goals per game",
        "FGA": "Field goal attempts per game",
        "FG%": "Field goal percentage",
        "3P": "Three-pointers per game",
        "3PA": "Three-point attempts per game",
        "3P%": "Three-point percentage",
        "2P": "Two-pointers per game",
        "2PA": "Two-point attempts per game",
        "2P%": "Two-point percentage",
        "EFG%": "Efficient field goals percent",
        "FT": "Free throws per game",
        "FTA": "Free throw attempts per game",
        "FT%": "Free throw percentage",
        "ORB": "Offensive rebounds",
        "DRB": "Defensive rebounds",
        "TRB": "Total rebounds",
        "AST": "Assists",
        "STL": "Steals",
        "BLK": "Blocks",
        "TOV": "Turnovers",
        "PF": "Personal fouls",
        "PTS": "Points"
    }

    column_descriptions_formatted = "\n".join(
        [
            f"- **{column_name}**: {description}"
            for column_name, description in column_descriptions.items()
            if column_name in column_names  # Only include descriptions for available columns
        ]
    )

    context = f"""
    Here is the table name <tableName> {table_name} </tableName>

    <tableDescription>{table_description}</tableDescription>

    Here are the player statistics available in the view:

    {column_descriptions_formatted}
        """
    return context



def get_system_prompt():
    google_sheet_data = get_table_from_sheet()  # Get Google Sheet data
    if google_sheet_data is not None:
        table_context = get_table_context(
            table_name=QUALIFIED_TABLE_NAME,
            table_description=TABLE_DESCRIPTION,
            rows=google_sheet_data.values.tolist()  # Convert DataFrame to a list of rows
        )
        return GEN_SQL.format(context=table_context)
    else:
        return "Error getting Google Sheet data"


# do `streamlit run prompts.py` to view the initial system prompt in a Streamlit app
if __name__ == "__main__":
    st.header("System prompt for Dan")
    st.markdown(get_system_prompt())

