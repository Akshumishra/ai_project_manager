INVITATION_EMAIL_SUBJECT = "Invitation to collaborate on {project_name}"

INVITATION_EMAIL_HTML_TEMPLATE = """
<div style="font-family: sans-serif; line-height: 1.5; color: #333;">
    <h2>Hello!</h2>
    <p><strong>{inviter_name}</strong> has invited you to collaborate on the project <strong>"{project_name}"</strong> in AI Project Manager.</p>
    <p>
        <a href="{frontend_url}/register?email={to_email}" 
           style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #fff; text-decoration: none; border-radius: 5px;">
           Get Started
        </a>
    </p>
    <p>If the button doesn't work, copy and paste this link: <br>
       {frontend_url}/register?email={to_email}</p>
    <p>Please register using this email (<strong>{to_email}</strong>) to start collaborating!</p>
    <hr>
    <p style="font-size: 0.8em; color: #777;">Best,<br>The AI Project Manager Team</p>
</div>
"""
