import csv
from typing import List, Optional
import requests
import aiohttp
from ragtrain.types import MCQ


def load_mcqlist_from_csv(csv_path: str):
    """
    Loads Q&A rows from a CSV file of the format:

    id,question,answer_0,answer_1,answer_2,answer_3,correct

    Returns:
        A list of MCQ objects.
    """
    mcq_list = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract the question and answers
            q_id = row["id"]
            question = row["question"]

            # Build a list of the 4 choices
            answers = [
                row["answer_0"],
                row["answer_1"],
                row["answer_2"],
                row["answer_3"],
            ]

            # Identify the index of the correct answer
            # e.g., correct column has the text that matches one of the answer_n
            correct_text = row["correct"]

            try:
                correct_index = answers.index(correct_text)
            except ValueError:
                # If we can't find an exact match, store -1 or handle gracefully
                correct_index = -1

            # Create a MCQ and store it
            qa_item = MCQ(q_id, question, answers, correct_index)
            mcq_list.append(qa_item)

    return mcq_list



def load_qaitems_from_gsheet(sheet_id: str, sheet_name: Optional[str] = None) -> List[MCQ]:
    """
    Loads Q&A items from a public Google Sheet.

    The sheet must be published to the web and have the following columns:
    id, question, answer_0, answer_1, answer_2, answer_3, correct

    Args:
        sheet_id: The ID of the Google Sheet (from the URL)
        sheet_name: Optional name of the specific sheet. If None, uses first sheet.

    Returns:
        List of MCQ objects
    """
    # Construct the URL for the published sheet in CSV format
    if sheet_name:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    else:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    # Fetch the data
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for bad status codes
    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch Google Sheet: {e}")

    # Parse CSV data
    qa_items = []
    csv_data = response.text

    # Handle empty response
    if not csv_data.strip():
        raise ValueError("Empty response from Google Sheet")

    # Parse rows
    try:
        reader = csv.DictReader(csv_data.splitlines())
        required_fields = {'id', 'question', 'answer_0', 'answer_1',
                           'answer_2', 'answer_3', 'correct'}

        # Verify headers
        headers = set(reader.fieldnames) if reader.fieldnames else set()
        missing_fields = required_fields - headers
        if missing_fields:
            raise ValueError(f"Missing required columns: {missing_fields}")

        # Process rows
        for row in reader:
            # Extract the question and answers
            q_id = row['id'].strip()
            question = row['question'].strip()

            # Build a list of the 4 choices
            answers = [
                row['answer_0'].strip(),
                row['answer_1'].strip(),
                row['answer_2'].strip(),
                row['answer_3'].strip(),
            ]

            # Identify the index of the correct answer
            correct_text = row['correct'].strip()

            try:
                correct_index = answers.index(correct_text)
            except ValueError:
                # If we can't find an exact match, try case-insensitive match
                lower_answers = [a.lower() for a in answers]
                try:
                    correct_index = lower_answers.index(correct_text.lower())
                except ValueError:
                    # If still no match, store -1
                    correct_index = -1

            # Create a MCQ and store it
            qa_item = MCQ(q_id, question, answers, correct_index)
            qa_items.append(qa_item)

    except csv.Error as e:
        raise ValueError(f"Failed to parse CSV data: {e}")

    return qa_items


async def aload_qaitems_from_gsheet(sheet_id: str, sheet_name: Optional[str] = None) -> List[MCQ]:
    """
    Async version of load_qaitems_from_gsheet.

    Args:
        sheet_id: The ID of the Google Sheet
        sheet_name: Optional name of the specific sheet

    Returns:
        List of MCQ objects
    """
    # Construct the URL
    base_url = "https://docs.google.com/spreadsheets/d"
    if sheet_name:
        url = f"{base_url}/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    else:
        url = f"{base_url}/{sheet_id}/gviz/tq?tqx=out:csv"

    # Fetch the data asynchronously
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                csv_data = await response.text()
        except aiohttp.ClientError as e:
            raise ValueError(f"Failed to fetch Google Sheet: {e}")

    # Handle empty response
    if not csv_data.strip():
        raise ValueError("Empty response from Google Sheet")

    # Parse CSV data (same as sync version)
    qa_items = []
    try:
        reader = csv.DictReader(csv_data.splitlines())
        required_fields = {'id', 'question', 'answer_0', 'answer_1',
                           'answer_2', 'answer_3', 'correct'}

        # Verify headers
        headers = set(reader.fieldnames) if reader.fieldnames else set()
        missing_fields = required_fields - headers
        if missing_fields:
            raise ValueError(f"Missing required columns: {missing_fields}")

        # Process rows
        for row in reader:
            q_id = row['id'].strip()
            question = row['question'].strip()

            answers = [
                row['answer_0'].strip(),
                row['answer_1'].strip(),
                row['answer_2'].strip(),
                row['answer_3'].strip(),
            ]

            correct_text = row['correct'].strip()

            try:
                correct_index = answers.index(correct_text)
            except ValueError:
                lower_answers = [a.lower() for a in answers]
                try:
                    correct_index = lower_answers.index(correct_text.lower())
                except ValueError:
                    correct_index = -1

            qa_item = MCQ(q_id, question, answers, correct_index)
            qa_items.append(qa_item)

    except csv.Error as e:
        raise ValueError(f"Failed to parse CSV data: {e}")

    return qa_items
