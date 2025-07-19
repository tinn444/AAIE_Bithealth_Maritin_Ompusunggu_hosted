import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import uvicorn
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()   


class PatientInfo(BaseModel):
    "Menentukan struktur data untuk informasi pasien yang diterima dari API."
    gender: str = Field(..., example="female", description="Terkait jenis kelamin pasien ('male', 'female')")
    age: int = Field(..., example=62, description="Usia pasien dalam tahun")
    symptoms: List[str] = Field(..., example=["pusing", "mual", "sulit berjalan"], description="Gejala yang dialami pasien, berupa daftar string")

class RecommendationResponse(BaseModel):
    "Mendefinisikan struktur data untuk respons rekomendasi yang dikembalikan oleh API."
    recommended_department: str = Field(..., example="Neurology", description="Departemen medis yang direkomendasikan berdasarkan gejala pasien")


# Instalasi FastAPI and Uvicorn
app = FastAPI(
    title="RujukCerdas API",
    description="Sebuah API untuk memberikan rekomendasi departemen medis berdasarkan data pasien.",
    version="1.0.0",
    contact={
        "name": "AI Triage System",
        "url": "http://example.com/contact",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mengizinkan semua origin untuk pengembangan
    allow_credentials=True,
    allow_methods=["*"],  # Mengizinkan semua metode (GET, POST, dll.)
    allow_headers=["*"],  # Mengizinkan semua header
)

try:
    #Mengambil API Key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables. Please create a .env file.")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_api_key)

    # Membuat Prompt Template, Tujuan untuk mengarahkan LLM dalam memberikan rekomendasi
    prompt_template_str = """
    Halo kamu adalah Triage system. Tugas kamu adalah menganalisis data pasien dan merekomendasikan departemen medis yang paling relevan.
    Tolong kamu hanya memberikan nama departemen yang direkomendasikan, tanpa penjelasan tambahan.:
    - Gender: {gender}
    - Age: {age}
    - Symptoms: {symptoms}

    Berdasarkan informasi yang telah diberikan, tentukan departemen spesialis yang paling sesuai Ya!
    Berikut adalah daftar departemen yang tersedia:
    - Cardiology (Jantung)
    - Neurology (Saraf)
    - Gastroenterology (Pencernaan)
    - Orthopedics (Tulang)
    - Pulmonology (Paru-paru)
    - Dermatology (Kulit)
    - Endocrinology (Hormon)
    - General Surgery (Bedah Umum)
    - Internal Medicine (Penyakit Dalam)

    Jawaban kamu harus berupa nama departemen yang paling sesuai dengan kondisi pasien.
    Pastikan untuk memberikan jawaban yang paling tepat berdasarkan gejala yang diberikan.
    """
    prompt = ChatPromptTemplate.from_template(prompt_template_str)
    output_parser = StrOutputParser()
    recommendation_chain = prompt | llm | output_parser

except Exception as e:
    print(f"Error during LLM setup: {e}")
    recommendation_chain = None
    
#Api Endpoints

@app.get("/", summary="Root Endpoint", description="A simple health check endpoint to confirm the server is running.")
async def read_root():

    return {"message": "Welcome to the RujukCerdas API. Use the /docs endpoint or http://127.0.0.1:8000/docs#/default/get_recommendation_recommend_post to get a department suggestion."}

@app.post("/recommend", response_model=RecommendationResponse, summary="Get Department Recommendation", description="Receives patient data and returns a recommended specialist department.")
async def get_recommendation(patient_info: PatientInfo):

    if recommendation_chain is None:
        raise HTTPException(
            status_code=500,
            detail="LLM service is not initialized. Check server logs for errors, likely a missing API key."
        )

    try:
        # Konversi symptom list dengan string yang dipisahkan koma
        symptoms_str = ", ".join(patient_info.symptoms)

        # Invoke LangChain berdasarkan data pasien
        response = await recommendation_chain.ainvoke({
            "gender": patient_info.gender,
            "age": patient_info.age,
            "symptoms": symptoms_str,
        })
        recommended_dept = response.strip()
        return RecommendationResponse(recommended_department=recommended_dept)

    except Exception as e:
        print(f"An error occurred while processing the request: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

if __name__ == "__main__":
    print("Starting FastAPI server...")
    print("Access the API docs at http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
