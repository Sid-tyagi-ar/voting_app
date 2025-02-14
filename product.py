import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import base64
import io
import random
import re
import dns.resolver
import traceback
from datetime import datetime

# Initialize Firebase with error handling
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
        })
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error("Failed to initialize Firebase connection")
    st.stop()

# Error logging function
def log_error(error_type, message):
    error_ref = db.collection('errors').document()
    error_ref.set({
        'timestamp': datetime.now(),
        'error_type': error_type,
        'message': message,
        'user_email': st.session_state.get('user_email', 'unknown'),
        'page': 'voting_interface'
    })

# Email validation functions
def is_valid_domain(domain):
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, 
            dns.resolver.NoNameservers, dns.resolver.Timeout):
        return False

def is_valid_email(email):
    try:
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            return False
            
        domain = email.split('@')[-1]
        with open('disposable_domains.txt') as f:
            disposable_domains = set(f.read().splitlines())
            
        if domain in disposable_domains:
            return False
            
        return is_valid_domain(domain)
    except Exception as e:
        log_error("EMAIL_VALIDATION_ERROR", str(e))
        return False

# Session management
def get_user_email():
    if 'user_email' not in st.session_state:
        with st.container():
            st.markdown("<div class='auth-section'>", unsafe_allow_html=True)
            email = st.text_input("📧 Enter your valid email address to vote:")
            
            if st.button("Start Voting"):
                email = email.strip().lower()
                if not is_valid_email(email):
                    st.error("Please enter a valid institutional email address")
                    log_error("INVALID_EMAIL_ATTEMPT", f"Invalid email tried: {email}")
                else:
                    st.session_state.user_email = email
                    st.rerun()
            
            st.markdown("""
            <div style="margin-top: 1rem; color: #666; font-size: 0.9rem;">
                <p>We verify emails to ensure fair voting:</p>
                <ul>
                    <li>✅ Valid institutional/organization email</li>
                    <li>❌ No disposable/temporary emails</li>
                    <li>🔒 Your email will only be used for vote tracking</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.stop()
    return st.session_state.user_email

# Profile management with error handling
def get_profiles():
    try:
        if 'profiles' not in st.session_state:
            profiles = db.collection("profiles").stream()
            profile_list = [{'id': p.id, **p.to_dict()} for p in profiles]
            random.shuffle(profile_list)
            st.session_state.profiles = profile_list
            st.session_state.profile_index = 0
    except Exception as e:
        log_error("PROFILE_LOAD_ERROR", str(e))
        st.error("Failed to load profiles. Please try again later.")
        st.stop()

# Voting system with transaction
def record_vote(profile_id):
    try:
        user_email = get_user_email()
        profile_ref = db.collection("profiles").document(profile_id)
        
        @firestore.transactional
        def vote_transaction(transaction):
            doc = transaction.get(profile_ref)
            profile_data = doc.to_dict()
            
            if user_email in profile_data.get('voted_by', []):
                return False
                
            transaction.update(profile_ref, {
                'votes': firestore.Increment(1),
                'voted_by': firestore.ArrayUnion([user_email])
            })
            return True
            
        return vote_transaction(db.transaction())
        
    except Exception as e:
        log_error("VOTING_ERROR", f"{str(e)} - Profile: {profile_id}")
        st.error("Failed to record vote. Please try again.")
        return False

# Main app interface
try:
    st.markdown("""
    <style>
    .profile-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        margin: 2rem auto;
        max-width: 600px;
    }
    .vote-buttons {
        margin-top: 1.5rem;
        gap: 1rem;
        display: flex;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

    get_profiles()
    get_user_email()

    # Profile display and voting
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
                        log_error("IMAGE_LOAD_ERROR", str(e))
                        st.error("Error loading profile image")
            
            with cols[1]:
                st.markdown(f"## {profile['name']}")
                st.markdown(f"**{profile['batch_year']} | {profile['gender']}**")
                st.markdown(profile['bio'])
                st.markdown(f"**Total Votes:** {profile.get('votes', 0)}")
                
                # Voting controls
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("❤️ Vote for this Profile"):
                        if record_vote(profile['id']):
                            st.success("Vote recorded!")
                            st.session_state.profile_index += 1
                            st.rerun()
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
                        if photo.size > 1048576:  # 1MB
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
                    log_error("PROFILE_SUBMIT_ERROR", str(e))
                    st.error("Failed to submit profile. Please try again.")

    # Leaderboard
    st.markdown("## 🏆 Current Leaderboard")
    try:
        leaderboard = sorted(st.session_state.profiles, 
                           key=lambda x: x.get('votes', 0), 
                           reverse=True)[:10]
        
        for idx, entry in enumerate(leaderboard):
            st.markdown(f"""
            <div style="padding: 1rem; margin: 0.5rem 0; border-radius: 10px; background: #f8f9fa;">
                <h4>#{idx+1} {entry['name']}</h4>
                <p>🎓 {entry['batch_year']} | {entry['gender']} | ❤️ {entry.get('votes', 0)} votes</p>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        log_error("LEADERBOARD_ERROR", str(e))
        st.error("Failed to load leaderboard")

except Exception as e:
    log_error("CRITICAL_ERROR", f"{str(e)}\n{traceback.format_exc()}")
    st.error("A critical error occurred. Our team has been notified.")
    st.stop()