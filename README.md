# WooCommerce to Google Sheets Integration

Kompleksowy system integrujący sklep WooCommerce z arkuszami Google Sheets, pozwalający na zarządzanie produktami z poziomu dedykowanego panelu oraz automatyczną synchronizację danych.

## 🚀 Architektura Systemu

System opiera się na architekturze mikroserwisów uruchamianych w kontenerach Docker:
- **FastAPI App (port 9000)**: Główna logika aplikacji, API oraz interfejs użytkownika.
- **WordPress/WooCommerce (port 8081)**: Sklep internetowy pełniący rolę bazy danych produktów.
- **MariaDB**: Baza danych dla WordPressa.
- **Ollama**: Lokalny serwer sztucznej inteligencji (LLM) do generowania opisów.
- **Google Sheets**: Zewnętrzny arkusz do synchronizacji danych.

---

## 📂 Przegląd Plików

### 🐍 Logika Pythona (Backend)

#### [main.py]
Serce aplikacji. Odpowiada za:
- Serwowanie interfejsu webowego (FastAPI + Jinja2).
- Obsługę API do tworzenia, edycji i usuwania produktów w WooCommerce.
- Specjalną obsługę zdjęć (Bypass): zdjęcia nie są pobierane przez WordPressa, lecz hostowane lokalnie w folderze `static/uploads/` i przesyłane jako linki w metadanych produktu (`_image_urls`).
- Integrację z modelami Ollama (`/api/generate-description`), pozwalającą na automatyczne pisanie opisów.
- Automatyczne wyzwalanie synchronizacji z Google Sheets po każdej zmianie.

#### [sheets_sync.py]
Moduł odpowiedzialny wyłącznie za integrację z Google Sheets:
- Wykorzystuje Google Sheets API v4.
- `sync_from_woo_to_sheets`: Pobiera wszystkie produkty z WooCommerce i nadpisuje arkusz Google.
- Obsługuje dwa typy autoryzacji: Service Account (`service_account.json`) lub User OAuth2 (`token.json`).

### 🌐 Interfejs Użytkownika (Frontend)

#### [templates/index.html]
Jednostronicowa aplikacja (SPA) oparta na Bootstrapie i jQuery:
- **Tabela Produktów**: Wykorzystuje DataTables do wyświetlania i wyszukiwania produktów.
- **Zarządzanie**: Formularze modalne do dodawania/edycji produktów.
- **Dashboard**: Szybkie linki do panelu administratora WooCommerce oraz bezpośrednio do arkusza Google Sheets.

### 🐳 Infrastruktura (Docker)

#### [docker-compose.yml]
Definiuje cały stos technologiczny. Zawiera automatyczną konfigurację WordPressa:
- Instaluje wtyczkę WooCommerce przy starcie.
- Konfiguruje stałe klucze API (`ck_...`, `cs_...`), aby aplikacja mogła od razu połączyć się ze sklepem.
- Uruchamia serwer Ollama z rezerwacją GPU, aby umożliwić szybkie działanie modeli językowych.

#### [Dockerfile]
Instrukcja budowania obrazu dla aplikacji FastAPI. Instaluje zależności z `requirements.txt` i uruchamia serwer `uvicorn`.

### 🐘 Skrypty PHP (Pomocnicze dla WordPress)

- **setup-api-keys.php**: Skrypt uruchamiany przez WP-CLI, który wstrzykuje klucze API bezpośrednio do bazy danych WordPressa.
- **force-ssl-rest.php**: Wtyczka typu "Must Use" (mu-plugin), która wymusza poprawne działanie API WooCommerce w środowisku Docker bez SSL.
- **force-basic-auth.php**: Pomocniczy skrypt do autoryzacji.

---

## ⚙️ Konfiguracja i Uruchomienie

1.  **Zależności Google**: 
    - Umieść plik `service_account.json` w głównym folderze.
    - Upewnij się, że Twoje konto serwisowe ma dostęp (edytowanie) do arkusza wskazanego przez `GOOGLE_SHEET_ID`.

2.  **Uruchomienie**:
    ```bash
    docker-compose up --build
    ```

3.  **Dostęp**:
    - Panel aplikacji: `http://localhost:9000`
    - WooCommerce Admin: `http://localhost:8081/wp-admin` (Login: `admin`, Hasło: `admin`)
    - Arkusz Google: Adres skonfigurowany w zmiennej środowiskowej.

---

## 🛠️ Funkcje Specjalne

- **Image Bypass**: Aplikacja nie zmusza WordPressa do "ściągania" zdjęć do swojej biblioteki mediów. Dzięki temu synchronizacja jest błyskawiczna, a linki w Google Sheets zawsze wskazują na oryginalne źródło lub lokalny hosting aplikacji.
- **AI Product Descriptions**: System korzysta z lekkiego, lokalnego modelu Ollama (domyślnie `llama3.2:1b`), aby na podstawie wygenerowanej nazwy produktu automatycznie pisać angażujące opisy po polsku. Zdejmuje to konieczność ręcznego pisania tekstów podczas testów i wypełniania bazy.
- **Automatyczna Synchronizacja**: Co 10 minut skrypt wykonuje pełny "Background Sync", aby upewnić się, że dane w Google Sheets są aktualne.
