import pandas as pd
import streamlit as st
from io import BytesIO
from zipfile import ZipFile

def create_excel_file(df):
    excel_file = BytesIO()
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
    excel_file.seek(0)
    return excel_file

def get_zipped_files(files):
    with BytesIO() as zipped_file:
        with ZipFile(zipped_file, 'w') as zf:
            for name, file in files:
                file.seek(0)
                zf.writestr(name, file.getvalue())
        zipped_file.seek(0)
        return zipped_file.getvalue()

def replace_words_v2(description, row):
    if not isinstance(description, str):  # Controleren of de beschrijving een string is
        return description
    
    for header in df.columns:
        st.write(header)
        st.write(row)
        if header in description:
            value = row[header]
            if pd.isna(value):  # Als de waarde NaN is, sla deze kolom over
                continue
            description = description.replace(f'[{header}]', str(value))
    return description

all_files = []
uploaded_file = st.file_uploader("Upload File", type="xlsx", accept_multiple_files=True)

if uploaded_file:
    files_to_process = uploaded_file if isinstance(uploaded_file, list) else [uploaded_file]
    
    for i, file in enumerate(files_to_process):
        df = pd.read_excel(file)
        df['Product description updated'] = df.apply(lambda row: replace_words_v2(row['Product description'], row), axis=1)
        excel_file = create_excel_file(df)
        all_files.append((f"{file.name}", excel_file))

    # If only one file is processed
    if len(all_files) == 1:
        file_name, file_data = all_files[0]
        st.download_button(label=f'Download {file_name}', data=file_data.getvalue(), file_name=file_name, key='single-file-button')

    # If multiple files are processed
    elif len(all_files) > 1:
        zipped_data = get_zipped_files(all_files)
        st.download_button(label='Download Zipped Excel Files', data=zipped_data, file_name='outputs.zip', key='zip-button')