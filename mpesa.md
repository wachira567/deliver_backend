# 💳 M-Pesa STK Push Configuration Guide

This guide explains how to set up the M-Pesa Daraja API for STK Push (Lipa Na M-Pesa Online) in the EventHub application.

## 1. Create a Safaricom Developer Account

1.  Go to the [Safaricom Developer Portal](https://developer.safaricom.co.ke/).
2.  Click **Login/Sign Up** and create an account.
3.  Log in to your account.

## 2. Create a New App

To get your API keys, you need to create an app on the portal.

1.  Click on **My Apps** in the top menu.
2.  Click **Create New App**.
3.  **App Name:** Enter a name (e.g., `EventHub-Dev`).
4.  **Products:** Ensure the **Lipa Na M-Pesa Sandbox** checkbox is selected.
    *   *Note: For production, you will need a live app with "Lipa Na M-Pesa" enabled.*
5.  Click **Create App**.

Once created, click on your app name to see your keys:
*   **Consumer Key**
*   **Consumer Secret**

## 3. Get Test Credentials (Sandbox)

For testing (Sandbox mode), you need a specific Shortcode and Passkey provided by Safaricom.

1.  Go to the **APIs** menu and select **MPesa Express** (or search for "Simulate").
2.  Alternatively, go to this direct link for [Test Credentials](https://developer.safaricom.co.ke/test_credentials).
3.  Copy the following values:
    *   **Business Shortcode** (usually `174379` for sandbox)
    *   **Lipa Na M-Pesa Online Passkey** (a long string starting with `bfb...`)

## 4. Configure Environment Variables

Open your `.env` file in the `Eventhub_Group_Backend` directory and update the following variables with the values you obtained above.

```ini
# .env

# 1. From your App in "My Apps"
MPESA_CONSUMER_KEY=your_consumer_key_here
MPESA_CONSUMER_SECRET=your_consumer_secret_here

# 2. From "Test Credentials" page
MPESA_SHORTCODE=174379
MPESA_LIPA_NA_MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919

# 3. Transaction Type (Do not change for Paybill)
MPESA_TRANSACTION_TYPE=CustomerPayBillOnline

# 4. Callback URLs
# IMPORTANT: These MUST be publicly accessible URLs (https).
# For local development, use ngrok (e.g., https://xyz.ngrok-free.app/api/mpesa/callback)
# For production, use your deployed domain.
MPESA_CALLBACK_URL=https://your-backend-url.onrender.com/api/mpesa/callback
```

### ⚠️ Important Note on Callback URLs

M-Pesa **cannot** send callbacks to `localhost`. You must use a public URL.

*   **Local Development:** Use [ngrok](https://ngrok.com/) to tunnel your localhost:
    ```bash
    ngrok http 5000
    ```
    Then copy the https URL (e.g., `https://1234abcd.ngrok.io`) and append `/api/mpesa/callback`.
*   **Production:** Use your actual domain (e.g., `https://eventhub-backend.onrender.com/api/mpesa/callback`).

## 5. Testing the Payment Flow

1.  Start your backend server.
2.  Open the EventHub frontend.
3.  Select an event and choose a ticket.
4.  Select "M-Pesa" as the payment method.
5.  Enter a **valid Safaricom number** (format: `0712345678` or `2547...`).
6.  Click **Pay**.
7.  Check your phone. You should receive a pop-up (STK Push) asking for your PIN.
    *   *Note: In Sandbox, even if you don't enter the PIN, you can simulate the completion.*

### Simulating Completion (Sandbox Only)

If you don't get the STK push (common in sandbox) or want to test the success flow without paying:

1.  The backend has a simulation endpoint.
2.  Check the backend logs for the `CheckoutRequestID` of the transaction you just initiated.
3.  Use Postman or curl to call:
    *   **POST** `/api/mpesa/simulate-complete/<transaction_id>`
    *   *Note: You'll need to find the internal transaction ID from the database or logs.*

## 6. Going Live

To go live, you need to:
1.  Apply for a Paybill/Till number from Safaricom.
2.  Create a "Live" app on the Developer Portal.
3.  Go through the "Go Live" process on the portal to verify your documents.
4.  Update the `.env` variables with your **Live** keys and Shortcode.
