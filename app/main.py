import streamlit as st
import base64
import io
import random
import traceback
from datetime import datetime
from PIL import Image
from firebase_admin import firestore

# Custom modules
from firebase_utils import initialize_firebase
from email_validation import is_valid_email
from logging_utils import log_error

# Initialize Firebase
try:
    db = initialize_firebase()
except Exception as e:
    st.error("Failed to initialize Firebase connection")
    st.stop()

# Session management
def get_user_email():
    if 'user_email' not in st.session_state:
        with st.container():
            st.markdown("<div class='auth-section'>", unsafe_allow_html=True)
            email = st.text_input("📧 Enter your valid institutional email address to vote:")
            
            if st.button("Start Voting"):
                email = email.strip().lower()
                if not is_valid_email(email):
                    st.error("Please enter a valid institutional email address (e.g., b22275@students.iitmandi.ac.in).")
                else:
                    st.session_state.user_email = email
                    st.rerun()
            
            st.markdown("""<div style="margin-top:1rem;color:#666;font-size:0.9rem">
                <p>We verify emails to ensure fair voting:</p>
                <ul>
                    <li>✅ Valid institutional email (e.g., b22275@students.iitmandi.ac.in)</li>
                    <li>❌ No personal or temporary emails</li>
                    <li>🔒 Your email will only be used for vote tracking</li>
                </ul>
            </div>""", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.stop()
    return st.session_state.user_email

# Profile management
def get_profiles():
    try:
        if 'profiles' not in st.session_state:
            profiles = db.collection("profiles").stream()
            profile_list = [{'id': p.id, **p.to_dict()} for p in profiles]
            random.shuffle(profile_list)
            st.session_state.profiles = profile_list
            st.session_state.profile_index = 0
    except Exception as e:
        log_error(db, "PROFILE_LOAD_ERROR", str(e))
        st.error("Failed to load profiles. Please try again later.")
        st.stop()

# Voting system
def record_vote(profile_id):
    try:
        user_email = get_user_email()
        profile_ref = db.collection("profiles").document(profile_id)
        
        # 1. Check local cache first
        if f"voted_{profile_id}" in st.session_state:
            return (False, "Already voted (local cache)")
        
        # 2. Server-side check with transaction
        @firestore.transactional
        def check_and_vote(transaction):
            doc = transaction.get(profile_ref)
            if not doc.exists:
                raise ValueError("Profile not found")
            
            voters = doc.get("voted_by", [])
            if user_email in voters:
                st.session_state[f"voted_{profile_id}"] = True  # Cache locally
                return False
                
            transaction.update(profile_ref, {
                "votes": firestore.Increment(1),
                "voted_by": firestore.ArrayUnion([user_email])
            })
            return True

        success = check_and_vote(db.transaction())
        
        if success:
            # Update local cache
            st.session_state[f"voted_{profile_id}"] = True
            return (True, "Vote recorded!")
        else:
            return (False, "Already voted (server check)")
            
    except Exception as e:
        log_error(db, "VOTING_ERROR", str(e))
        return (False, f"Voting failed: {str(e)}")
# Main app
try:
    st.markdown("""
    <style>
    .leaderboard-entry {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        background: var(--background-color);
        color: var(--text-color);
        border: 1px solid var(--border-color);
    }
    
    /* Light theme */
    [data-theme="light"] .leaderboard-entry {
        --background-color: #f8f9fa;
        --text-color: #000000;
        --border-color: #e0e0e0;
    }
    
    /* Dark theme */
    [data-theme="dark"] .leaderboard-entry {
        --background-color: #2e2e2e;
        --text-color: #ffffff;
        --border-color: #444444;
    }
    </style>
    """, unsafe_allow_html=True)

    get_profiles()
    get_user_email()

    # Display current profile
    if st.session_state.profile_index < len(st.session_state.profiles):
        profile = st.session_state.profiles[st.session_state.profile_index]
        
        with st.container():
            st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
            
            cols = st.columns([1, 2])
            with cols[0]:
                if profile.get("photo"):
                    try:
                        img_bytes = base64.b64decode(profile["photo"])
                        st.image(Image.open(io.BytesIO(img_bytes)), use_container_width=True)
                    except Exception as e:
                        log_error(db, "IMAGE_LOAD_ERROR", str(e))
                        st.error("Error loading profile image")
            
            with cols[1]:
                st.markdown(f"## {profile['name']}")
                st.markdown(f"**{profile['batch_year']} | {profile['gender']}**")
                st.markdown(profile['bio'])
                st.markdown(f"**Total Votes:** {profile.get('votes', 0)}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("❤️ Vote for this Profile"):
                        success, error_msg = record_vote(profile['id'])
                        if success:
                            st.success("Vote recorded!")
                            st.session_state.profile_index += 1
                            st.rerun()
                        elif error_msg:
                            st.error(f"Failed to record vote: {error_msg}")
                        else:
                            st.warning("You've already voted for this profile!")
                with col2:
                    if st.button("⏭ Skip Profile"):
                        st.session_state.profile_index += 1
                        st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("## 🎉 You've Viewed All Profiles!")
        if st.button("🔄 Start Over with New Random Order"):
            random.shuffle(st.session_state.profiles)
            st.session_state.profile_index = 0
            st.rerun()

    # Profile submission
    with st.sidebar.expander("➕ Nominate New Profile"):
        with st.form("nomination_form", clear_on_submit=True):
            name = st.text_input("Full Name")
            batch_year = st.selectbox("Batch Year", ["2025", "2024", "2023", "2022"])
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            bio = st.text_area("Short Bio (max 150 chars)", max_chars=150)
            photo = st.file_uploader("Profile Photo (max 1MB)", type=["jpg", "png"])
            
            if st.form_submit_button("Submit Nomination"):
                try:
                    photo_data = None
                    if photo:
                        if photo.size > 1048576:
                            st.error("Image exceeds size limit")
                        else:
                            photo_data = base64.b64encode(photo.read()).decode("utf-8")
                    
                    new_profile = {
                        "name": name.strip(),
                        "batch_year": batch_year,
                        "gender": gender,
                        "bio": bio.strip(),
                        "votes": 0,
                        "voted_by": [],
                        "photo": photo_data,
                        "timestamp": datetime.now()
                    }
                    
                    db.collection("profiles").add(new_profile)
                    st.success("Profile submitted!")
                    get_profiles()
                    
                except Exception as e:
                    log_error(db, "PROFILE_SUBMIT_ERROR", str(e))
                    st.error("Failed to submit profile. Please try again.")

    # Leaderboard
    # Leaderboard
    st.markdown("## 🏆 Current Leaderboard")
    try:
        leaderboard = sorted(st.session_state.profiles, 
                           key=lambda x: x.get('votes', 0), 
                           reverse=True)[:10]
        
        for idx, entry in enumerate(leaderboard):
            st.markdown(f"""
            <div class="leaderboard-entry">
                <h4>#{idx+1} {entry['name']}</h4>
                <p>🎓 {entry['batch_year']} | {entry['gender']} | ❤️ {entry.get('votes', 0)} votes</p>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        log_error(db, "LEADERBOARD_ERROR", str(e))
        st.error("Failed to load leaderboard")

except Exception as e:
    log_error(db, "CRITICAL_ERROR", f"{str(e)}\n{traceback.format_exc()}")
    st.error("A critical error occurred. Our team has been notified.")
    st.stop()
