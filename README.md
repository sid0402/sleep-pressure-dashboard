# sleep-pressure-dashboard

## Inspiration
Sleep problems at hospitals is something that I've always known about through my own personal experiences. There is no denying that your own bed is just that much better than that of a hospital's! However, the problem is far bigger that I had thought. Some simple statistics show this:
- **76% of hospitalized patients report poor sleep quality**
- **Adults in hospitals sleep 1.3-3.2 hours less per night than the recommended amount**
- **Above 40% of ICU patients are at risk of developing pressure ulcers**
- **26.8 billion dollars are spent on pressure ulcer treatment in the USA annually!**

When I found a dataset that tracked sleep data through pressure,  I knew I wanted to improve the current sleeping standards at hospitals.

## What it does
RestAssure is a smart patient monitoring system that:
- Classifies a **patient's current sleep posture** using a trained CNN model
- Tracks pressure accumulation over different body regions
- Records posture as **FHIR Observations** to integrate seamlessly into current hospital EHRs
- Visualizes pressure heatmaps and posture change patterns using sleep pressure data
- Sends **automated SMS alerts to nurses for high-risk cases**
- **Logs all actions** and sleep events for auditing and compliance

## How I built it
- **Hardware Input**: Simulated pressure mat data (64x32) over time
- **ML Mode**l: Trained CNN in PyTorch to classify postures (supine, left, right)
- **Flask Backend**: Serves real-time API endpoints and performs sleep posture classification
- **FHIR Integration**: Posts sleep posture events as standardized FHIR Observation resources using a local HAPI FHIR server
- **Frontend**: Interactive dashboard using vanilla JS, HTML/CSS — includes heatmaps, tooltip insights, and posture change chart
- **Alert System**: Sends high-risk SMS notifications using Textbelt
- **Audit Logging**: Records all nurse-patient interactions in a dedicated audit_logs table
- **Deployment**: Dockerized with a dedicated app for logs viewer on a separate port

## Challenges I ran into
- Ensuring accurate classification of sleep posture with limited labeled data
- Mapping pressure regions consistently from high-res frames to an 8x4 grid
- Building a visually rich yet low-latency frontend for real-time monitoring
- Integrating with FHIR correctly — understanding Observation structure, patient references, and REST interactions
- Managing user authentication and per-unit access for nurses securely

## Accomplishments that I'm proud of
- Built a full-stack patient monitoring system from scratch
- Integrated with the industry-standard FHIR protocol
- Implemented real-time posture recognition + risk visualization
- Designed an intuitive and interactive UI that nurses can actually use
- Created an audit logging system to meet healthcare compliance
- Built our own Docker-deployed FHIR server using HAPI-FHIR JPA
- Implementing the real-time text messaging system in case of high risk

## What I learned
- How FHIR data standards work and why they're important in healthcare
- Implementing CNNs for image-based classification in practical workflows
- How to build audit logs that track sensitive healthcare events securely, with HIPAA standards in mind

## What's next for RestAssure
- Improve pressure prediction using temporal models like LSTMs or transformers. This will account for the previous pressure data, thereby improving how the risk is calculated
- Add more sleeping data through wearable devices, to make an end-to-end sleeping solution for hospitals
- Integrate live hardware from pressure sensor mats

## References
1. **Github Repo for Machine Learning Model Inspiration**: [link](https://github.com/Fustincho/UD-Private-In-bed-Posture-Classification)

2. **Pressure Map dataset:** [link](https://archive.physionet.org/pn6/pmd/)

3. “76% of hospitalized patients report poor sleep quality”, "Hospitalized adults sleep 1.3–3.2 h less than recommended for healthy people": [link](https://pmc.ncbi.nlm.nih.gov/articles/PMC9672415/#:~:text=Of%20all%20studies%2C%2076%25%20reported,than%20recommended%20for%20healthy%20people.)

4. **“Above 40% of ICU patients are at risk of developing pressure ulcers”**:
[link](https://pmc.ncbi.nlm.nih.gov/articles/PMC5359849/)

5. **“Pressure Ulcers - 26.8 billion dollars spent annually”**[link](https://pmc.ncbi.nlm.nih.gov/articles/PMC10553030/)

