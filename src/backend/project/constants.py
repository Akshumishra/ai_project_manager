INVITATION_EMAIL_SUBJECT = "Invitation to collaborate on {project_name}"

INVITATION_EMAIL_HTML_TEMPLATE = """
<div style="font-family: sans-serif; line-height: 1.5; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
    <h2 style="color: #007bff;">Hello!</h2>
    <p><strong>{inviter_name}</strong> has invited you to collaborate on the project <strong>"{project_name}"</strong> in AI Project Manager.</p>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="{frontend_url}/register?email={to_email}" 
           style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: #fff; text-decoration: none; border-radius: 5px; font-weight: bold; margin-bottom: 10px;">
           Get Started
        </a>
        <br>
        <a href="{slack_workspace_invite_url}" 
           style="display: inline-block; padding: 10px 20px; background-color: #4A154B; color: #fff; text-decoration: none; border-radius: 5px; font-weight: bold;">
           Join Project Workspace on Slack
        </a>
    </div>

    <p>Please register on our platform using this email (<strong>{to_email}</strong>) to start collaborating!</p>
    <p>If the "Get Started" button doesn't work, copy and paste this link: <br>
       <span style="color: #007bff;">{frontend_url}/register?email={to_email}</span></p>
    
    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 0.8em; color: #777;">Best,<br>The AI Project Manager Team</p>
</div>
"""