# SmartInbox: Technical Architecture & Code Implementation Guide

This guide provides a deep dive into the **SmartInbox** codebase, explaining how the architectural concepts are implemented across the Backend, Frontend, and Machine Learning pipeline.

---

## 1. Backend Architecture (FastAPI)

The backend is a high-performance REST API built with FastAPI, designed for asynchronous execution and production-grade reliability.

### 🚀 Application Entrypoint (`Backend/main.py`)
- **Concept**: The hub where everything is wired together.
- **Implementation**: 
  - **Lifespan Manager**: Uses `@asynccontextmanager` to handle startup logic. It verifies database connectivity, runs migrations (`create_tables`), and initializes the ML detector (`init_spam_detector`) before the server accepts requests.
  - **Middleware stack**: Includes `GZipMiddleware` for compression, `CORSMiddleware` for cross-origin access, and custom `GlobalExceptionMiddleware` to ensure the API never leaks raw Python errors to the user.
  - **Router Registration**: Routes are organized under the `/api/v1` prefix for versioning, covering `auth`, `user`, `admin`, and `notifications`.

### 🗄️ Persistence Layer (`Backend/database.py` & `Backend/models/`)
- **Concept**: Mapping code to database tables.
- **Implementation**:
  - **SQLAlchemy Async**: Uses `create_async_engine` and `AsyncSessionLocal` for non-blocking database operations.
  - **Models**: `models/prediction.py` defines the `Prediction` table which stores the message ID, classification result (spam/ham), and model confidence probability.

### 🧠 Business Logic (`Backend/services/`)
- **Concept**: Separation of concerns; keeping the "how" separate from the "what."
- **Implementation**:
  - **`prediction_service.py`**: The heart of the app. It handles:
    - **Single Prediction**: Calls the ML detector, stores the result, and tracks latency.
    - **Batch Processing**: Uses `asyncio.gather` and `asyncio.Semaphore(5)` to process multiple messages in parallel without overwhelming the database.
    - **Analytics**: Calculates global spam rates and daily trends using SQL aggregation functions (`func.count`, `func.date`).

### 🔐 Security (`Backend/auth/`)
- **Concept**: Protecting user data and admin routes.
- **Implementation**:
  - **JWT Tokens**: Uses `OAuth2PasswordBearer` with `jose` for signing JSON Web Tokens. 
  - **Password Hashing**: Uses `passlib` with `bcrypt` to securely store user credentials.

---

## 2. Machine Learning Pipeline (`ml/`)

The ML layer is responsible for turning raw SMS text into a numeric spam probability.

### 🛠️ Feature Engineering (`ml/feature_pipeline.py`)
- **Concept**: Transforming text into numbers.
- **Implementation**:
  - **Text Preprocessing**: A pipeline that cleans text (lowercase, punctuation removal), tokenizes it using `nltk`, and applies lemmatization to reduce words to their base forms.
  - **TF-IDF Vectorization**: Uses two separate TF-IDF models:
    - **Word-level**: Captures the meaning of words (unigrams/bigrams).
    - **Char-level**: Handles spelling tricks (e.g., "S P A M") using 3-5 character n-grams.
  - **Numeric Features**: Extracts length, special character counts, and digit density as additional signals.

### 🏗️ Model Training (`ml/train_robust.py`)
- **Concept**: Training a model that doesn't just memorize data.
- **Implementation**:
  - **Stacking Classifier**: Combines multiple models (Random Forest, Logistic Regression) to improve overall accuracy and reduce variance.
  - **Robustness**: Implements k-fold cross-validation and hyperparameter tuning to ensure the model generalizes to real-world SMS data.

### 🔌 ML Service (`Backend/services/ml_service.py`)
- **Concept**: The bridge between the API and the model file.
- **Implementation**:
  - **SpamDetectorService**: Loads the `.pkl` (pickle) model file into memory. It provides a `predict()` method that takes raw text, runs it through the `SMSFeaturePipeline`, and returns a dictionary with the verdict and probability.

---

## 3. Frontend Architecture (React / Vite)

A modern, responsive dashboard that visualizes backend data and provides interactive tools.

### 📡 Data Fetching (`Frontend/src/api/`)
- **Concept**: Talking to the backend.
- **Implementation**:
  - **`axiosClient.js`**: Centralized Axios instance. It features **Interceptors** that automatically attach the JWT token to every request and handle `401 Unauthorized` errors by redirecting the user to the login page.
  - **`spamApi.js`**: A collection of functions like `predictText()`, `getSpamTrends()`, and `exportHistory()` that wrap individual API endpoints.

### 📊 Visualization (`Frontend/src/components/charts/`)
- **Concept**: Making data actionable through visuals.
- **Implementation**:
  - **Recharts Integration**: Uses `<AreaChart>` and `<PieChart>` to display the daily spam trends and overall classification distribution. Data fetched from `/user/spam-trends` is mapped directly to the chart data format.

### 🎛️ State Management (`Frontend/src/store/` or `context/`)
- **Concept**: Managing app-wide data (like the logged-in user).
- **Implementation**:
  - **AuthContext**: A React Context provider that wraps the entire app, making `user` info and `login/logout` functions available to any component.

---

## 4. Deployment & Infrastructure

### ☁️ Cloud Platforms
- **Render (`render.yaml`)**:
  - Defines the **Web Service** (Backend) and a **Worker Service** (for background analytics).
  - Automates environment setup using `pip install` and `download_nltk.py`.
- **AWS Amplify (`amplify.yml`)**:
  - Automates the Frontend build process using `npm install` and `npm run build`, then hosts the static artifacts on a global CDN.

### 📜 Scripts & Automation
- **`.bat` files**: Allow Windows developers to start the frontend or backend with a single click.
- **`.sh` files**: Used in production containers to run database migrations and start the Gunicorn/Uvicorn server.
- **`run.py`**: A helper script that provides a clean CLI for starting the FastAPI app with specific production configurations.
