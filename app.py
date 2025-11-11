import streamlit as st
import requests
import time

st.title("Sales Argumentation")


def query_api(prompt: str) -> str:
    """

    :param prompt: (str) User message
    :return:
        response (str): Assistant response
    """

    url = "https://teqmr90em4.execute-api.eu-west-1.amazonaws.com/test/prompt"
    payload = {
        "prompt": f"{prompt}"
    }
    headers = {"Content-Type": "application/json",
               "authorizationToken": "testStreamlit"}

    try:
        response = requests.get(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()['body']

    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")  # e.g. 404 Not Found
    except requests.exceptions.ConnectionError:
        print("Error connecting to the server.")
    except requests.exceptions.Timeout:
        print("Request timed out.")
    except requests.exceptions.RequestException as err:
        print(f"An unexpected error occurred: {err}")


def response_generator(response: str):
    for word in response.split():
        yield word + " "
        time.sleep(0.08)


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("How can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = st.write_stream(response_generator(query_api(prompt)))
    st.session_state.messages.append({"role": "assistant", "content": response})


