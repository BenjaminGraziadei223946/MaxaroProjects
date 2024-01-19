import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from openai import AzureOpenAI
import streamlit as st
from io import BytesIO
import os

st.title("Product Text Generator")

found_placeholder = st.empty()
searched_placeholder = st.empty()

if 'count_searched' not in st.session_state:
    st.session_state['count_searched'] = 0

if 'count_found' not in st.session_state:
    st.session_state['count_found'] = 0

main_page = "https://www.maxaro.nl"
df_prodDes = pd.DataFrame(columns=['Product', 'Description', 'URL'])

client = AzureOpenAI(
    api_key = st.secrets['api_key'],
    api_version = "2023-05-15",
    azure_endpoint = st.secrets['azure_endpoint']
    )

tries = 0
def generate_description(url, soup):
    global tries
    global df_prodDes
    product_title = soup.find('h1', class_='product-header__title').get_text().strip()
    if product_title:

        specifications_container = soup.find('div', id="specifications")
        specs = specifications_container.find('div', class_="product-detail-specifications").get_text().strip() if specifications_container else st.write(f"Specifications not found for {product_title}")


        benefits_container = soup.find('div', id="benefits")
        benefits = benefits_container.find('div', class_="product-detail-section__content").get_text().strip() if benefits_container else st.write(f"Benefits not found for {product_title}")
        
        if specs or benefits:
            text = f"{product_title}: {specs}. {benefits}"

            response = client.chat.completions.create(
                model="gpt-35-turbo",
                messages = [
                    {"role": "system", "content": "Maak een overtuigende en positieve productbeschrijving voor het volgende artikel. Benadruk de belangrijkste kenmerken, voordelen en onderscheidende kenmerken. Gebruik duidelijke en begrijpelijke taal om de lezer te boeien. Stel je voor dat je tegen een potentiële klant spreekt die op zoek is naar de beste kwaliteiten van het product. Maak de beschrijving ongeveer 150-200 woorden. Verder moet de tekst seo-geoptimaliseerd zijn, dus kijk uit naar: Schrijf voor kopers, niet voor bots; Leg de nadruk op voordelen, voeg functies toe; Richt je op de juiste SEO-productzoekwoorden; Plaats zoekwoorden strategisch in je tekst; Laat de lengte afhangen van het bewustzijn van de koper; Maak een duidelijke oproep tot actie; Maak unieke productbeschrijvingen voor elk PDP"},
                    {"role": "user", "content": f"Dit is het product waarvoor we een beschrijving nodig hebben: {text}"},
                ])
            new_row = {'Product': product_title, 'Description': response.choices[0].message.content, 'URL': url}
            df_prodDes.loc[len(df_prodDes)] = new_row
            tries = 0
        elif tries < 3:
            tries += 1
            time.sleep(2)
            generate_description(url, soup)
    elif tries < 3:
        tries += 1
        time.sleep(2)
        generate_description(url, soup)
    return None

def check_product_descriptions(url):
    url = url.strip()  # Remove any leading/trailing whitespace
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        p_tag = soup.find('p', string='Productomschrijving')

        if not p_tag:
            st.session_state['count_found'] += 1
            found_placeholder.write(f'Found: {st.session_state["count_found"]}')
            generate_description(url, soup)
    else:
        time.sleep(2)
        check_product_descriptions(url)

    return None

def is_button_disabled(button):
    if button.get('disabled'):
        return True
    if 'is-disabled' in button.get('class', ''):
        return True
    return False

def get_category_links(url, max_attempts=3, delay=2):                                                               # Get the links of the categories on Mainpage
    for attempt in range(max_attempts):
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            category_container = soup.find('div', class_='categories-with-icon__container')
            if category_container:
                category_link_elements = category_container.find_all('a', class_='categories-with-icon__item')
                if category_link_elements:
                    return [link['href'] for link in category_link_elements if 'href' in link.attrs]                # return the links of the categories
        time.sleep(delay)
    return None

def get_sub_links(url, max_attempts=3, delay=2):                                                                   # Get the links of the subcategories inside the categories           
    for attempt in range(max_attempts):
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            sub_container = soup.find('div', class_='categories-with-image')
            if sub_container:
                sub_link_elements = sub_container.find_all('a', class_='categories-with-image__item')             
                if sub_link_elements:
                    return [link['href'] for link in sub_link_elements if 'href' in link.attrs]                    # return the links of the subcategories
            else:
                return None
        time.sleep(delay)
    return None

def get_product_links(url, max_attempts=3, delay=2):                                                                 # Get the links of the products on given page
    for attempt in range(max_attempts):                                                                                 # Loop as long as there are more pages
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            product_container = soup.find_all('div', class_='column is-6-mobile is-4-tablet')                   # Find all the products on the page

            next_page_span = soup.find('span', class_='pagination__button-text', string='Volgende')           # Find the next page button text
            next_page_button =  next_page_span.find_parent('a') if next_page_span else None   
            if len(product_container) != 24:
                                # Find the next page button parent
                if next_page_button and not is_button_disabled(next_page_button):
                    continue
            for product in product_container:
                try:
                    link = product.find('a')['href']
                    st.session_state['count_searched'] += 1
                    searched_placeholder.write(f'Searched: {st.session_state["count_searched"]}')
                    check_product_descriptions(main_page + link)
                except TypeError as e:
                    print('No link found',e , product)
                
            if next_page_button and not is_button_disabled(next_page_button):                               # Check if the button is disabled and if not, get the link
                url = main_page + next_page_button['href']                                                  # Update the url          
            else:                                                                                           # If the button is disabled, break the loop                        
                break

        time.sleep(delay)
    return None

def get_links(main_page):
    def format(link):
        return link.split('/')[-2]

    if 'selected_categories' not in st.session_state:
        st.session_state['selected_categories'] = []

    if 'subcategories' not in st.session_state:
        st.session_state['subcategories'] = {}

    categories = get_category_links(main_page)
    formatted_categories = [format(x) for x in categories]

    selected_categories = st.multiselect('Select Categories', formatted_categories, key='cat_select')

    if selected_categories != st.session_state['selected_categories']:
        # New selection made, reset subcategories
        st.session_state['subcategories'] = {}
        st.session_state['selected_categories'] = selected_categories

    for category in selected_categories:
        if category not in st.session_state['subcategories']:
            category_url = main_page + '/' + category
            st.session_state['subcategories'][category] = get_sub_links(category_url)

    urls = []
    for category in selected_categories:
        subcategories = st.session_state['subcategories'].get(category, [])
        
        if subcategories:
            formatted_subcategories = [format(x) for x in subcategories]
            selected_subcategories = st.multiselect(f'Select Subcategories for {category}', formatted_subcategories, default=formatted_subcategories, key=f'sub_select_{category}')

            for sub_link in selected_subcategories:
                sub_url = main_page + '/' + category + '/' + sub_link
                generate_description(sub_url)
        else:
            category_url = main_page + '/' + category
            generate_description(category_url)

    if st.button("Start", key='start'):
        for url in urls:    
            get_product_links(url)


    return None


get_links(main_page)
#check_product_descriptions('https://www.maxaro.nl/douches/douchecabines/diamond-douchecabine-90x90-cm-mat-zwart-helder-glas-draaideur-vierkant-154119/')

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

if not df_prodDes.empty:
    df_xlsx = to_excel(df_prodDes)
    st.download_button(label='Download Excel file',
                    data=df_xlsx ,
                    file_name='product_descriptions.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')