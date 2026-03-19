OTP_EXPIRY_SECONDS = 600  # 10 minutes
OTP_RESEND_DELAY = 60    # 1 minute

OTP_EMAIL_SUBJECT = "Verification Code for AI Project Manager"

OTP_EMAIL_HTML_TEMPLATE = """
<html>
    <body style="font-family: sans-serif; line-height: 1.5; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
            <h2 style="color: #007bff;">Your Verification Code</h2>
            <p>Hello,</p>
            <p>Your verification code is: <strong style="font-size: 1.2em; letter-spacing: 2px;">{otp_code}</strong></p>
            <p>This code will expire in 10 minutes.</p>
            <p>If you did not request this code, please ignore this email.</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 0.8em; color: #777;">Best,<br>The AI Project Manager Team</p>
        </div>
    </body>
</html>
"""
