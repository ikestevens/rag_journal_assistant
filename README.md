# RAG Journal Assistant

![RAG Journal Assistant Logo](logo.png)

## How To Use Your Own Journal

Extract insights from your journal by replacing 'dummy_journal_data.csv' with your own journal csv. Also replace where this data is referenced in journal_rag_helpers.py by changing the name there (line 10). The journal data must be in csv format with Year, Month (as a string fully spelt out), Day, Entry. See the dummy_journal_data.csv for examples. Dummy data is only from January 2023 to March 2023 if you use the app with it.

## Running the Streamlit App To Query the Journal

This application can be run in two ways: using Docker or directly with Python. Choose the method that best suits your environment and follow the corresponding steps.

### Option 1: Using Docker

1. **Set up the `.env` file**

   First, you need to create a `.env` file in the root directory of the project. This file should contain your OpenAI API key. Create the file and add the following line:

   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

   Replace `your_openai_api_key_here` with your actual OpenAI API key.

2. **Build and Run the Docker Container**

   Open a terminal in the project directory. Build the Docker image and run the container using the following commands:

   ```bash
   docker build -t rag-journal-app .
   docker run --env-file .env -p 8501:8501 rag-journal-app
   ```

   This will start the Streamlit app, which you can access by navigating to `http://localhost:8501` in your web browser.

### Option 2: Using Python

1. **Set the `OPENAI_API_KEY` Environment Variable**

   Before running the app, you need to set the `OPENAI_API_KEY` environment variable to your OpenAI API key. This can be done in your terminal as follows:

   - On Linux/Mac:

     ```bash
     export OPENAI_API_KEY=your_openai_api_key_here
     ```

   - On Windows:

     ```cmd
     set OPENAI_API_KEY=your_openai_api_key_here
     ```

   Replace `your_openai_api_key_here` with your actual OpenAI API key.

2. **Create a Virtual Environment**

   Navigate to the project directory and create a Python virtual environment:

   ```bash
   python -m venv journal
   ```

   Activate the virtual environment:

   - On Linux/Mac:

     ```bash
     source journal/bin/activate
     ```

   - On Windows:

     ```cmd
     .\journal\Scripts\activate
     ```

3. **Install the Requirements**

   Install the required Python packages using:

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Streamlit App**

   With the setup complete, you can now run the Streamlit app:

   ```bash
   streamlit run app.py
   ```

   The app should now be running and accessible via `http://localhost:8501` in your web browser.
   If using dummy data, try asking "What were some things I loved doing in January 2023?"
