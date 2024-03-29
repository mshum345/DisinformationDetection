import csv
import google.generativeai as genai
import os
import uuid
from helper_functions.email_functions import send_email
import pandas as pd


def run_prompt(api_key, prompt, email, base_url, num_rows=300):
    if num_rows > 500 or num_rows < 1:
        print("Too many or too few rows requested, using the default of 300")
        num_rows = 300
    # Declare main variables
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    datasets_directory = os.path.join(parent_directory, "Datasets")
    in_file = os.path.join(datasets_directory, "WELFake", "WELFake_Dataset_5000.csv")
    out_file_name = str(uuid.uuid4()) + ".csv"
    out_file = os.path.join(script_directory, "dynamic", "prompt_results", out_file_name)
    file_download_path = base_url + f"download/{out_file_name}"
    data = []
    dataset_name = "WELFake Dataset"
    subject = "US_politics"
    i = 0
    stats = {"tPos": 0, "tNeg": 0, "fPos": 0, "fNeg": 0, "num_correct": 0, "num_rows": num_rows}

    # Configure Gemini API
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name='gemini-pro')

    # # Pulls data in from csv file and organizes it in a list of dictionaries
    # with open(in_file, 'r', encoding='utf-8', errors='ignore') as in_csv:
    #     reader = csv.DictReader(in_csv)
    #     in_data = list(reader)
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(in_file, header=0)

    # Skip the first row (headers)
    df = df.iloc[1:]

    # Shuffle the DataFrame
    df = df.sample(frac=1)

    # Grab the first num_rows rows
    random_rows = df.head(num_rows)

    # Establish headers
    headers = [
        "id", "dataset", "text", "subject", "prompt", "label", "response", "confidence_level", "truth_level", "correct", "response_explanation"
    ]

    # Write the header row
    with open(out_file, mode="a", newline="", encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(headers)

    # Loops through every row of data in the csv file
    num_iters = 0
    for index, row in random_rows.iterrows():
        print(str(num_iters) + ":")
        try:
            num_iters += 1
            # Add text to current prompt and strips text of any ";"
            full_prompt = prompt + row["text"].replace(";", "")

            # Interact with Gemini to fill out response, response_explanation, confidence, truthful_level, and correct
            res = model.generate_content(
            contents=full_prompt,
            generation_config={
            'temperature': 0,
            'max_output_tokens': 800
            },
            safety_settings=[
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS",
                "threshold": "BLOCK_NONE",
            },
            ])

            # Checks if the prompt was blocked
            if str(res.prompt_feedback).replace("\n", "") == "block_reason: OTHER":
                print(str(i) + ": Prompt Blocked")
                continue

            # Checks for if response is empty
            if res.parts == []:
                print(str(i) + ": Response is empty")
                continue

            #print(res.text)
            res = res.text.split(";")

            # Checks if response is correct length
            if len(res) <= 1:
                print("Prompt did not return correct response")
                continue
            
            # Determines if AI was correct or not
            label = int(row["label"])
            if label == 0:
                if str(label) == str(res[0]):
                    correct = 1
                    stats["num_correct"] += 1
                    stats["tPos"] += 1
                else:
                    correct = 0
                    stats["fNeg"] += 1
            else:
                if str(label) == str(res[0]):
                    correct = 1
                    stats["num_correct"] += 1
                    stats["tNeg"] += 1
                else:
                    correct = 0
                    stats["fPos"] += 1

            # Create the new row of data for output csv
            new_list = []
            new_list.append(i) # id
            new_list.append(dataset_name) # dataset
            new_list.append(row["text"]) # text
            new_list.append(subject) # subject
            new_list.append(prompt.replace("\n", "")) # prompt
            new_list.append(row["label"]) # label
            new_list.append(res[0]) # response
            new_list.append(res[1]) # confidence_level
            new_list.append(res[2]) # truth_level
            new_list.append(correct) # correct
            new_list.append(res[3]) # response_explanation

            data.append(new_list)

            if num_iters % 50 == 0:
                with open(out_file, mode="a", newline="", encoding='utf-8') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerows(data)
                
                # Clear the data list after writing to the CSV file
                data = []

        except Exception as e:
            print(f"(server error) Exception: {str(e)}")
            continue  # Move on to the next iteration


    # Write the data to the out_file csv
    if data:
        with open(out_file, mode="a", newline="", encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(data)


    # Send CSV file as attachment via email
    send_email(email, file_download_path, stats, prompt)

    return