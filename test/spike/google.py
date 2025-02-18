from serpapi import GoogleSearch
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import re


def get_text_from_url(url):
    response = requests.get(url, stream=True)
    if "text/html" in response.headers.get("Content-Type", ""):
        return BeautifulSoup(response.text, "html.parser").get_text()
    # elif "application/pdf" in response.headers.get("Content-Type", ""):
    #     return "\n".join(page.get_text() for page in fitz.open(stream=response.content, filetype="pdf"))
    else:
        return response.text  # For plain text or other formats


def get_content_from_google(k, query):
    params = {
        "q": query,
        "api_key": "bc2eded1806d27e795a23a7e512b6188dccb39115abcdb3d89fab90c1af7dd8d",
        "num": 10,  # Get more results
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    import pdb; pdb.set_trace()
    organic_results = results["organic_results"]
    search_content = {}
    count = 0
    for result in organic_results:
        snippet = result['snippet']
        link = result['link']
        content = snippet
        try:
            content = get_text_from_url(link)
            content = re.sub(r'\s+', ' ', content).strip()
        except Exception:
            content = snippet
        search_content[link] = content
        count += 1
        if count == k:
            break
    return search_content


if __name__ == '__main__':
    # Example usage
    print(get_content_from_google(3, "The Flavr Savr Tomato:,is a variety of vine-ripened tomato in the supermarket,was created to have better flavor and shelf-life,does not undergo soft rot,all of the above,all of the above"))


