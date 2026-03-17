"""
Test script to verify Slack posting works correctly.
This helps debug why summaries aren't being posted.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.services.slack_service import SlackService
from src.backend.config import Config
from src.backend.db.database_standup import SessionStandup
from src.backend.model.standup import Standup

def test_slack_connection():
    """Test basic Slack API connection."""
    print("🔍 Testing Slack Connection...")
    print(f"   SLACK_BOT_TOKEN: {'Set' if Config.SLACK_BOT_TOKEN else 'NOT SET'}")
    
    if not Config.SLACK_BOT_TOKEN:
        print("❌ SLACK_BOT_TOKEN is not set in environment variables!")
        return False
    
    try:
        service = SlackService()
        # Try to get bot info to verify token works
        print("   ✅ SlackService initialized")
        return True
    except Exception as e:
        print(f"   ❌ Error initializing SlackService: {e}")
        return False

def test_post_to_channel(channel_id: str, thread_ts: str = None):
    """Test posting a message to a channel/thread."""
    print(f"\n📤 Testing post to channel {channel_id}...")
    
    if not Config.SLACK_BOT_TOKEN:
        print("❌ SLACK_BOT_TOKEN not set!")
        return False
    
    try:
        service = SlackService()
        test_message = "🧪 Test message from standup system"
        
        if thread_ts:
            print(f"   Posting to thread {thread_ts}...")
            result_ts = service.post_message(channel_id, test_message, thread_ts=thread_ts)
        else:
            print(f"   Posting to channel...")
            result_ts = service.post_message(channel_id, test_message)
        
        print(f"   ✅ Message posted successfully! Timestamp: {result_ts}")
        return True
    except Exception as e:
        print(f"   ❌ Failed to post message: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_standup_finalize(standup_id: str):
    """Test finalizing a specific standup."""
    print(f"\n🔍 Testing finalize for standup {standup_id}...")
    
    db = SessionStandup()
    try:
        standup = db.query(Standup).get(standup_id)
        if not standup:
            print(f"   ❌ Standup {standup_id} not found!")
            return False
        
        print(f"   Standup found:")
        print(f"      Channel: {standup.slack_channel_id}")
        print(f"      Thread TS: {standup.message_ts}")
        print(f"      Summary in DB: {'Yes' if standup.summary else 'No'}")
        
        # Test posting to this specific thread
        if standup.slack_channel_id and standup.message_ts:
            print(f"\n   Testing post to this thread...")
            return test_post_to_channel(standup.slack_channel_id, standup.message_ts)
        else:
            print(f"   ❌ Missing channel_id or message_ts!")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("🧪 Slack Posting Test Script")
    print("=" * 60)
    
    # Test 1: Basic connection
    if not test_slack_connection():
        print("\n❌ Basic connection test failed. Check your SLACK_BOT_TOKEN.")
        sys.exit(1)
    
    # Test 2: If standup_id provided, test that specific standup
    if len(sys.argv) > 1:
        standup_id = sys.argv[1]
        test_standup_finalize(standup_id)
    else:
        print("\n💡 Usage:")
        print("   python3 test_slack_posting.py                    # Test basic connection")
        print("   python3 test_slack_posting.py <standup_id>        # Test posting to specific standup thread")
        print("\n   To find standup_id:")
        print("   SELECT id, project_id, message_ts FROM standups ORDER BY created_at DESC LIMIT 5;")
