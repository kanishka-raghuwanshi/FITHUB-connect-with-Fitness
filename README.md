# FITHUB - Connect to Fitness

A comprehensive fitness tracking application built with **Python**, **Streamlit**, and **SQLite**. FITHUB connects users with professional trainers, allowing them to subscribe to fitness plans, follow trainers, and communicate through real-time chat.

---

## Features

### Authentication System
- **Secure Signup/Login** for both Trainers and Regular Users
- **Password Hashing** with salt using SHA-256
- **Token-based Authentication** with 7-day expiry
- Automatic token refresh on login

### Trainer Dashboard
- **Create Fitness Plans** with:
  - Title (e.g., "Fat Loss Beginner Plan")
  - Description
  - Price (numeric)
  - Duration (e.g., 30 days)
  - Difficulty Level
  - Category
- **Edit or Delete** their own plans
- **View Subscribers** and follower statistics
- **Update Profile** (specialization, experience, bio)

### User Subscriptions
- **Browse All Plans** with filtering options
- **Subscribe to Plans** (simulated payment)
- **Access Control**:
  - Non-subscribers see only: Title, Trainer Name, Price
  - Subscribers get full plan details

### Follow System
- **Follow/Unfollow Trainers**
- **View Followed Trainers** list with profiles

### Personalized Feed
- Plans from **followed trainers**
- **Purchased plans** with status
- Trainer info in each feed item

### Real-time Chat
- Message trainers and other users
- Contact list with unread indicators
- Full conversation history

### Workout & Goals Tracking
- Log daily workouts
- Set and track fitness goals
- Progress monitoring

---

## Prerequisites

Before running FITHUB, ensure you have the following installed:

- **Python 3.8 or higher**
- **pip** (Python package manager)

---

## Installation & Running on VS Code

### Step 1: Clone or Download the Project

If you downloaded a ZIP file, extract it to your desired location.

### Step 2: Open in VS Code

1. Open **Visual Studio Code**
2. Go to `File` > `Open Folder`
3. Select the project folder containing `app.py`

### Step 3: Create a Virtual Environment (Recommended)

Open the integrated terminal in VS Code (`Ctrl + `` ` or `View` > `Terminal`):

\`\`\`bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
\`\`\`

### Step 4: Install Dependencies

\`\`\`bash
pip install streamlit
\`\`\`

Or install from pyproject.toml:

\`\`\`bash
pip install -e .
\`\`\`

### Step 5: Run the Application

\`\`\`bash
streamlit run app.py
\`\`\`

The app will automatically open in your default browser at `http://localhost:8501`

---

## Project Structure

\`\`\`
fithub/
├── app.py              # Main application file
├── pyproject.toml      # Project configuration
├── README.md           # This file
└── fitness.db          # SQLite database (auto-generated)
\`\`\`

---

## Database Schema

FITHUB uses SQLite with the following tables:

| Table | Description |
|-------|-------------|
| `users` | User accounts with authentication tokens |
| `trainers` | Trainer profiles and specializations |
| `fitness_plans` | Workout plans created by trainers |
| `subscriptions` | User subscriptions to plans |
| `followers` | User-trainer follow relationships |
| `messages` | Chat messages between users |
| `workouts` | User workout logs |
| `goals` | User fitness goals |

---

## Usage Guide

### For New Users

1. Click **"Sign Up"** on the home page
2. Select account type: **User** or **Trainer**
3. Fill in your details and create account
4. Login with your credentials

### For Trainers

1. Login to your trainer account
2. Navigate to **"Create Plan"** tab
3. Fill in plan details (title, description, price, duration)
4. Manage your plans in **"My Plans"** tab
5. View subscribers and respond to messages

### For Users

1. Login to your user account
2. Browse available plans in **"Browse Plans"**
3. Subscribe to plans you like
4. Follow trainers to see their content in your feed
5. Chat with trainers for guidance

---

## Troubleshooting

### Common Issues

**Issue: `streamlit` command not found**
\`\`\`bash
pip install streamlit --upgrade
\`\`\`

**Issue: Module not found error**
\`\`\`bash
pip install -r requirements.txt
# or
pip install streamlit
\`\`\`

**Issue: Port 8501 already in use**
\`\`\`bash
streamlit run app.py --server.port 8502
\`\`\`

**Issue: Database errors**
Delete `fitness.db` file and restart the app (database will be recreated)

---

## VS Code Extensions (Recommended)

For the best development experience, install these extensions:

- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **SQLite Viewer** (qwtel.sqlite-viewer)

---

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **Database**: SQLite
- **Authentication**: SHA-256 password hashing with salt
- **Session Management**: Token-based with 7-day expiry

---

## Security Features

- Password hashing with random salt
- Secure token generation using `secrets` module
- Token expiration for session security
- Access control for plan details
- Input validation on all forms

---

## License

This project is open source and available for educational purposes.

---

## Support

If you encounter any issues or have questions, please check the troubleshooting section above or create an issue in the repository.

---

**FITHUB - Connect to Fitness** | Built with Streamlit and Python
