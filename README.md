# dhan-edis
Automated eDIS authorization for [https://dhan.co/](https://dhan.co/)

This script streamlines the eDIS authorization process for [https://dhan.co/](https://dhan.co/)
without the need for browser automation tools like Selenium. The primary
advantage of this approach is its efficiency on small virtual machines,
especially those with limited resources where running browsers like
Google Chrome might be challenging due to high memory consumption.

## Usage
Before integrating this script into your project, I recommend thorough
testing to validate its functionality and to ensure compatibility with
your specific use case. The script has been designed to automate the
eDIS authorization flow exclusively through the API, eliminating the
need for browser involvement.

## Instructions

1. Clone this repository to your local machine.
2. Navigate to the project directory and install all dependencies.
3. Customize the script if needed, and ensure it aligns with your project requirements.
4. Update the required environment variables:
    ```
    DHAN_ACCESS_TOKEN
    DHAN_CLIENT_ID
    DHAN_TPIN
    ```
5. This script requires permissions to read email for the authorization OTP. It assumes
   that the email is hosted on Gmail. Follow the Google's app setup guide mentioned on
   [this page](https://developers.google.com/gmail/api/quickstart/python) to get
   programmatic access to your Gmail account. When the script is executed for the first
   time, it will prompt you to authorize access to your Gmail account and download the
   credentials file. This setup is required only once.
6. Execute the script:
    ```bash
    python main.py
    ```
7. Monitor the output for any error messages or unexpected behavior.
