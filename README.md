# DeTox

A web-app that detects toxicity (curse, insult, threat, hate, etc.) in
YouTube comments and deletes them.

### Contents:
- <b>notebooks</b> - Jupyter Notebooks containing exploratory data analysis, training and evaluation part of the machine learning model.
- <b>app</b> - Implementation of the web-app which connects to youtube account, displays channel data, analyzes latest three video's and deletes (rejects) toxic comments found in them.

### Dataset:
- [Toxic Comment Classification Challenge - Kaggle](https://www.kaggle.com/competitions/jigsaw-toxic-comment-classification-challenge/data)

### Summary of Implementation:

- Performed exploratory data analysis on the data such as finding no. of instances per class, finding null values, determining max len for the comment.
- Divided the data into train and test set by using stratified sampling technique to maintain class ratio in both set.
- Fine-tuned the BERT model using PyTorch and Hugging Face transformers libraries, evaluated its performance and saved the model. [Fine Tuned Toxicity Detection Model .pth file](https://mega.nz/file/ojMDCQyK#m-mTe4VsldWhgrP4qWPrX3GqvgdTQaELqytXKiP3ryg)
- Developed a web-app that connects with youtube, accesses the comments of videos and deletes (rejects) toxic comments using FastAPI Framework.
- Used Google OAuth 2.0 and YouTube Data API to authorize and get access to youtube channel.
- Created various views (web-pages) that helps user to navigate through the web-app.
- Integrated the trained ML model with the web-app to classify and delete comments of the selected video.

### Getting Started:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/HDV998/SE-project.git
    cd DeTox
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Download the Model**:
    - Download the fine-tuned model from the link in "Summary of Implementation".
    - Place `toxic_model.pth` in `app/machine_learning/model_hub/fine_tuned/`.

4.  **Setup Environment Variables**:
    - Create a `.env` file in the `app/` directory.
    - Add your Google OAuth credentials:
      ```env
      CLIENT_ID=your_client_id
      CLIENT_SECRET=your_client_secret
      SCOPE=https://www.googleapis.com/auth/youtube.force-ssl
      REDIRECT_URIS=http://localhost:8000/auth/oauth2callback
      STATE=random_string
      SESSION_SECRET=random_string
      ```

5.  **Run the Application**:
    ```bash
    uvicorn app.main:app --reload
    ```

### Web-App Demo:


https://user-images.githubusercontent.com/65736401/206852378-18015e0a-56f7-47ba-8472-4c0207b3eb86.mp4

