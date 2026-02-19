# 🔄 Workflows & Architecture

<div align="center">

### [🏠 Home](README.md) &nbsp;|&nbsp; [🎨 Figma Design](FIGMA.md) &nbsp;|&nbsp; [🔄 Workflows](WORKFLOWS.md)

</div>

---

The application is designed with clear, simplified workflows for each user type.

## Visitor Journey
*From landing page to dashboard.*

```mermaid
flowchart TD
    A[Start] --> B[Open Website]
    B --> C[View Home Page]
    C --> D[Read About App]
    D --> E{Interested?}
    E -- Yes --> F[Sign Up or Log In]
    E -- No --> G[Leave Website]
    F --> H[Dashboard]
    G --> I[End]
    H --> I
```

## Regular User Journey

### 1. Check SMS
*The core functionality for verifying messages.*

```mermaid
flowchart TD
    A[Start] --> B[Log In]
    B --> C[User Dashboard]
    C --> D[Paste SMS Message]
    D --> E[Click 'Check Message']
    E --> F{Result}
    F -->|Spam| G[View Warning]
    F -->|Not Spam| H[View Safe Status]
    G --> I[End]
    H --> I
```

### 2. View Statistics
*Understanding spam trends.*

```mermaid
flowchart TD
    A[Start] --> B[Dashboard]
    B --> C[Open Statistics]
    C --> D[Select Time Range]
    D --> E[View Spam Trends Graph]
    E --> F[End]
```

### 3. Upload Multiple Messages
*Batch processing for high-volume checks.*

```mermaid
flowchart TD
    A[Start] --> B[Dashboard]
    B --> C[Upload CSV/Text File]
    C --> D[System Processes File]
    D --> E[View Batch Results]
    E --> F[End]
```

## Admin Journey
*System management and configuration.*

```mermaid
flowchart TD
    A[Start] --> B[Admin Log In]
    B --> C[Admin Dashboard]
    C --> D[View System Metrics]
    D --> E[Adjust Spam Threshold]
    E --> F[Save Configuration]
    F --> G[End]
```

## Overall System Flow
*High-level view of the entire application structure.*

![System Flow](assets/image.png)

```mermaid
flowchart TD
    A[Open App] --> B{Auth Status}
    B -- Guest --> C[Log In / Register]
    B -- User --> D[Dashboard]
    C --> D
    
    subgraph Dashboard Features
    D --> E[Check Single Message]
    D --> F[View Statistics]
    D --> G[Batch Upload]
    end
    
    E --> H[Logout]
    F --> H
    G --> H
    H --> I[End]
```

## 🚀 Summary

A quick overview of the primary user loop:

```mermaid
flowchart LR
    A(Login) --> B(Check SMS)
    B --> C(View Result)
    C --> D(View Stats)
    D --> E(Logout)
```
