"""
Script to verify if a message was actually posted to Slack.
This helps debug why the API says success but message doesn't appear.
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.db.database_standup import SessionStandup
from src.backend.model.standup import Standup
from src.backend.services.slack_service import SlackService

def verify_standup_summary(standup_id: str):
    """Verify if the standup summary was actually posted to Slack."""
    db = SessionStandup()
    
    try:
        # Convert string to UUID
        try:
            standup_uuid = uuid.UUID(standup_id)
        except ValueError:
            print(f"❌ Invalid UUID format: {standup_id}")
            return
        
        standup = db.query(Standup).filter(Standup.id == standup_uuid).first()
        if not standup:
            print(f"❌ Standup {standup_id} not found!")
            return
        
        print(f"📋 Standup ID: {standup_id}")
        print(f"   Channel: {standup.slack_channel_id}")
        print(f"   Thread TS: {standup.message_ts}")
        print(f"   Summary in DB: {'Yes' if standup.summary else 'No'}")
        
        if not standup.summary:
            print("\n❌ No summary found in database. Finalize may not have completed successfully.")
            return
        
        print(f"\n📝 Summary stored in DB (first 200 chars):")
        print(f"   {standup.summary[:200]}...")
        
        # Try to verify by fetching thread replies
        print(f"\n🔍 Verifying message in Slack...")
        try:
            service = SlackService()
            
            # Fetch all replies in the thread
            replies = service.list_replies(standup.slack_channel_id, standup.message_ts)
            
            print(f"   Found {len(replies)} messages in thread")
            
            # Check if summary appears in any reply
            summary_found = False
            for i, reply in enumerate(replies):
                text = reply.get("text", "")
                user = reply.get("user", "")
                ts = reply.get("ts", "")
                
                # Check if this looks like our summary
                if "Standup Summary" in text or "✅" in text and "Standup Summary" in text:
                    summary_found = True
                    print(f"\n   ✅ Summary found in thread!")
                    print(f"      Message TS: {ts}")
                    print(f"      User: {user}")
                    print(f"      Preview: {text[:100]}...")
                    break
            
            if not summary_found:
                print(f"\n   ⚠️  Summary NOT found in Slack thread!")
                print(f"   This means:")
                print(f"      1. The Slack API call may have succeeded but message wasn't posted")
                print(f"      2. The message was posted to wrong channel/thread")
                print(f"      3. There's a delay in Slack updating")
                print(f"\n   Check:")
                print(f"      - Is the bot in the channel?")
                print(f"      - Does the bot have permission to post?")
                print(f"      - Is the channel_id correct? ({standup.slack_channel_id})")
                print(f"      - Is the thread_ts correct? ({standup.message_ts})")
                
                # Show all replies for debugging
                print(f"\n   All messages in thread:")
                for i, reply in enumerate(replies, 1):
                    text = reply.get("text", "")[:50]
                    user = reply.get("user", "")
                    ts = reply.get("ts", "")
                    print(f"      {i}. User: {user}, TS: {ts}, Text: {text}...")
            
        except Exception as e:
            print(f"   ❌ Error verifying in Slack: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 verify_slack_message.py <standup_id>")
        print("\nExample:")
        print("   python3 verify_slack_message.py ab07093e-0383-4c43-9206-27ea1c02d8f3")
        sys.exit(1)
    
    standup_id = sys.argv[1]
    verify_standup_summary(standup_id)
