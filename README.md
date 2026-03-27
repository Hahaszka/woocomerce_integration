# WooCommerce & Google Sheets Sync Manager

Profesjonalny system do zarządzania produktami w sklepie WooCommerce z automatyczną synchronizacją z Arkuszami Google. Aplikacja zbudowana w oparciu o FastAPI, Docker oraz Bootstrap 5.

## 🚀 Główne Funkcje

- **Zarządzanie Produktami (CRUD)**: Dodawanie, edycja i usuwanie produktów bezpośrednio z przejrzystego panelu webowego.
- **Dwukierunkowa Synchronizacja**: Automatyczne przesyłanie danych o produktach z WooCommerce do Arkuszy Google.
- **Obsługa Mediów**: Możliwość wgrywania zdjęć z dysku lokalnego (z automatyczną kompresją do formatu JPG) lub podawania adresów URL.
- **Synchronizacja Okresowa**: Aplikacja automatycznie odświeża dane w Arkuszach Google co 10 minut.
- **Nowoczesny Interfejs**: Responsywny panel użytkownika wykorzystujący Bootstrap 5 oraz DataTables do szybkiego wyszukiwania i sortowania produktów.
- **Pełna Konteneryzacja**: Gotowe środowisko Docker Compose zawierające WordPress, MariaDB oraz aplikację synchronizującą.

## 🛠️ Wymagania Wstępne

Przed uruchomieniem upewnij się, że masz zainstalowane:
- **Docker** oraz **Docker Compose**
- Dostęp do API WooCommerce (klucze `Consumer Key` i `Consumer Secret`)
- Projekt w Google Cloud z włączonym **Google Sheets API**
- Plik `service_account.json` (klucz konta serwisowego Google)

## ⚙️ Konfiguracja

Aplikacja konfiguruje się automatycznie na podstawie zmiennych środowiskowych w pliku `docker-compose.yml`:

| Zmienna | Opis |
| :--- | :--- |
| `WOO_URL` | Adres URL Twojego sklepu WooCommerce |
| `WOO_KEY` | Consumer Key z ustawień REST API WooCommerce |
| `WOO_SECRET` | Consumer Secret z ustawień REST API WooCommerce |
| `GOOGLE_SHEET_ID` | Identyfikator Arkusza Google (widoczny w URL arkusza) |

### Klucze Google
Umieść plik `service_account.json` w głównym katalogu projektu. Upewnij się, że adres e-mail konta serwisowego ma uprawnienia edycji do Twojego arkusza Google.

## 📦 Instalacja i Uruchomienie

1. **Sklonuj repozytorium** i przejdź do folderu projektu.
2. **Skonfiguruj zmienne** w `docker-compose.yml`.
3. **Uruchom kontenery**:
   ```bash
   docker-compose up -d --build
   ```
4. **Dostęp do aplikacji**:
   - Panel zarządzania: `http://localhost:9000`
   - Lokalny WordPress (testowy): `http://localhost:8081` (użytkownik: `admin`, hasło: `admin`)

## 📋 Struktura Arkusza

Podczas synchronizacji aplikacja tworzy/aktualizuje arkusz o następujących kolumnach:
1. **ID** - Unikalny identyfikator produktu w WooCommerce.
2. **Name** - Nazwa produktu.
3. **Price** - Cena regularna.
4. **Description** - Opis produktu (z oczyszczonymi tagami HTML).
5. **Image URLs** - Linki do zdjęć produktu rozdzielone przecinkami.

## 📁 Struktura Projektu

- `main.py` - Główny moduł FastAPI obsługujący API i UI.
- `sheets_sync.py` - Logika integracji z Google Sheets API.
- `static/uploads/` - Katalog na wgrane lokalnie zdjęcia produktów.
- `templates/` - Szablony HTML (Jinja2).
- `docker-compose.yml` - Definicja całego stosu technologicznego.

## 📝 Uwagi
- Zdjęcia wgrywane lokalnie są dostępne pod adresem `http://app:8000/static/uploads/` (wewnątrz sieci Docker).
- Przy pierwszym uruchomieniu aplikacja pobiera wszystkie produkty z WooCommerce i wysyła je do arkusza.
