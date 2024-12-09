from flask import Flask, render_template, request, Response, jsonify
import pandas as pd
from unicodedata import normalize
from urllib.parse import unquote
import html
from yt_dlp import YoutubeDL
import librosa
import tempfile
import os
from pydub import AudioSegment

app = Flask(__name__)  # This should be before any route decorators

# Load the CSV file
df = pd.read_csv('data/songs.csv')

# Preprocess data
def preprocess_data(df):
    # List of text columns
    text_columns = ['Main Artist', 'Featuring', 'Song', 'Genre', 'Language', 'Country', 'Arrangement', 'Key']
    
    # Create normalized versions of text columns
    for col in text_columns:
        # Create a new column with normalized data
        df[col + '_normalized'] = df[col].fillna('').apply(
            lambda x: normalize('NFKD', x).encode('ascii', errors='ignore').decode('utf-8').lower()
        )
    
    # Convert 'Year Released' and 'BPM' to numeric types
    df['Year Released'] = pd.to_numeric(df['Year Released'], errors='coerce')
    df['BPM'] = pd.to_numeric(df['BPM'], errors='coerce')
    
    # Drop rows with missing or invalid numeric data and reset index
    df = df.dropna(subset=['Year Released', 'BPM']).reset_index(drop=True)
    df['Year Released'] = df['Year Released'].astype(int)
    df['BPM'] = df['BPM'].astype(int)
    
    # Split comma-separated values and normalize them
    multi_valued_columns = ['Country', 'Language', 'Arrangement', 'Genre']
    for col in multi_valued_columns:
        # Keep original list as lists of items
        df[col] = df[col].fillna('').apply(
            lambda x: [item.strip() for item in x.split(',')] if x else []
        )
        # Create normalized version
        df[col + '_normalized'] = df[col].apply(
            lambda x: [normalize('NFKD', item).encode('ascii', errors='ignore').decode('utf-8').lower() for item in x]
        )

    # Create BPM Range (grouped by ranges of 10)
    df['BPM Range'] = (df['BPM'] // 10) * 10  # Groups like 100, 110, etc.

    # Create Year Range (grouped by decades)
    df['Year Range'] = (df['Year Released'] // 10) * 10  # Decades like 1990, 2000, etc.

    return df

df = preprocess_data(df)

def download_audio_from_youtube(url):
    """Download audio from YouTube URL"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'temp_%(id)s.%(ext)s'
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            return f"temp_{info['id']}.mp3", info
        except Exception as e:
            raise Exception(f"Failed to download: {str(e)}")

def extract_audio_features(audio_path):
    """Extract audio features using librosa"""
    try:
        # Load the audio file
        y, sr = librosa.load(audio_path)
        
        # Extract features
        # Get tempo (BPM)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        # Convert tempo to float first, then round to integer
        tempo_float = float(tempo)
        bpm = int(round(tempo_float))
        
        # Get key
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key_idx = int(chroma.mean(axis=1).argmax())
        key = key_names[key_idx]
        
        # Get duration
        duration = librosa.get_duration(y=y, sr=sr)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        duration_str = f"{minutes}:{seconds:02d}"
        
        return {
            'BPM': bpm,
            'Key': key,
            'Duration': duration_str
        }
    except Exception as e:
        print(f"Error in extract_audio_features: {str(e)}")  # Debug logging
        raise Exception(f"Failed to extract features: {str(e)}Hey")

@app.route('/')
def home():
    categories = ['Key', 'BPM', 'Genre', 'Language', 'Country', 'Year Released', 'Arrangement', 'Stats']
    
    # Prepare all songs data
    songs = []
    for _, row in df.iterrows():
        featuring = row['Featuring']
        if pd.isna(featuring):
            featuring = ''
        else:
            featuring = str(featuring).strip()

        # Create a normalized search string
        search_terms = []
        for col in ['Main Artist', 'Song', 'Featuring', 'Key']:
            normalized_col = col + '_normalized'
            value = row.get(normalized_col, '')
            if isinstance(value, list):
                # Join list items with space
                value = ' '.join(value)
            search_terms.append(str(value))
        search_string = ' '.join(search_terms)
        search_string = html.escape(search_string)

        song = {
            'Main Artist': row['Main Artist'],
            'Song': row['Song'],
            'Featuring': featuring,
            'Duration': row['Duration'],
            'Year Released': int(row['Year Released']),
            'BPM': row['BPM'],
            'Key': row['Key'],
            'search_string': search_string
        }
        songs.append(song)
    
    return render_template('home.html', categories=categories, songs=songs)

@app.route('/category/<category_name>')
def category(category_name):
    category_name = category_name.strip()
    if category_name == 'BPM':
        bpm_ranges = sorted(df['BPM Range'].unique())
        values = []
        for bpm_range in bpm_ranges:
            count = df[df['BPM Range'] == bpm_range].shape[0]
            values.append((str(bpm_range), f"{bpm_range}-{bpm_range + 9}", count))
    elif category_name == 'Year Released':
        year_ranges = sorted(df['Year Range'].unique())
        values = []
        for year_range in year_ranges:
            count = df[df['Year Range'] == year_range].shape[0]
            values.append((str(year_range), f"{year_range}-{year_range + 9}", count))
    elif category_name in ['Country', 'Language', 'Arrangement', 'Genre']:
        normalized_col = category_name + '_normalized'
        original_col = category_name
        value_counts = {}
        for idx, row in df.iterrows():
            normalized_values = row[normalized_col]
            original_values = row[original_col]
            for norm_val, orig_val in zip(normalized_values, original_values):
                key = (norm_val, orig_val)
                if key in value_counts:
                    value_counts[key] += 1
                else:
                    value_counts[key] = 1
        values = [(norm_val, orig_val, count) for (norm_val, orig_val), count in value_counts.items()]
        values.sort(key=lambda x: x[1])
    else:
        values_series = df[[category_name + '_normalized', category_name]].drop_duplicates()
        values = []
        for idx, row in values_series.iterrows():
            norm_val = row[category_name + '_normalized']
            orig_val = row[category_name]
            count = df[df[category_name + '_normalized'] == norm_val].shape[0]
            values.append((norm_val, orig_val, count))
        values.sort(key=lambda x: x[1])

    return render_template('category.html', category=category_name, values=values)

@app.route('/category/<category_name>/<subcategory_value>')
def subcategory(category_name, subcategory_value):
    category_name = category_name.strip()
    normalized_subcategory_value = unquote(subcategory_value).lower().strip()

    original_subcategory = subcategory_value  # Default fallback

    if category_name == 'BPM':
        try:
            bpm_range = int(normalized_subcategory_value)
        except ValueError:
            return "Invalid BPM range.", 400
        filtered_df = df[df['BPM Range'] == bpm_range]
        original_subcategory = f"{bpm_range}-{bpm_range + 9}"
    elif category_name == 'Year Released':
        try:
            year_range = int(normalized_subcategory_value)
        except ValueError:
            return "Invalid Year range.", 400
        filtered_df = df[df['Year Range'] == year_range]
        original_subcategory = f"{year_range}-{year_range + 9}"
    elif category_name in ['Country', 'Language', 'Arrangement', 'Genre']:
        # Find the original value from the dataframe
        matched_rows = df[df[category_name + '_normalized'].apply(lambda x: normalized_subcategory_value in x)]
        if not matched_rows.empty:
            # Iterate through the rows to find the exact original subcategory
            for _, row in matched_rows.iterrows():
                original_values = row[category_name]
                for orig_val in original_values:
                    normalized_orig_val = normalize('NFKD', orig_val).encode('ascii', errors='ignore').decode('utf-8').lower()
                    if normalized_orig_val == normalized_subcategory_value:
                        original_subcategory = orig_val
                        break
                else:
                    continue
                break
        else:
            return f"No songs found for {category_name}: {subcategory_value.capitalize()}.", 404
    else:
        matched_rows = df[df[category_name + '_normalized'] == normalized_subcategory_value]
        if not matched_rows.empty:
            original_subcategory = matched_rows.iloc[0][category_name]
        else:
            return f"No songs found for {category_name}: {subcategory_value}.", 404

    # Prepare songs data
    songs = []
    filtered_df = df[df.apply(
        lambda row: (
            (category_name == 'BPM' and row['BPM Range'] == int(normalized_subcategory_value)) or
            (category_name == 'Year Released' and row['Year Range'] == int(normalized_subcategory_value)) or
            (category_name in ['Country', 'Language', 'Arrangement', 'Genre'] and normalized_subcategory_value in row[category_name + '_normalized']) or
            (not category_name in ['BPM', 'Year Released', 'Country', 'Language', 'Arrangement', 'Genre'] and row[category_name + '_normalized'] == normalized_subcategory_value)
        ),
        axis=1
    )]

    for _, row in filtered_df.iterrows():
        # Handle NaN in 'Featuring' field
        featuring = row['Featuring']
        if pd.isna(featuring):
            featuring = ''
        else:
            featuring = str(featuring).strip()

        # Create a normalized search string
        search_terms = []
        for col in ['Main Artist', 'Song', 'Featuring', 'Key']:
            normalized_col = col + '_normalized'
            value = row.get(normalized_col, '')
            if isinstance(value, list):
                # Join list items with space
                value = ' '.join(value)
            search_terms.append(str(value))
        search_string = ' '.join(search_terms)
        search_string = html.escape(search_string)

        song = {
            'Main Artist': row['Main Artist'],
            'Song': row['Song'],
            'Featuring': featuring,
            'Duration': row['Duration'],
            'Year Released': int(row['Year Released']),
            'BPM': row['BPM'],
            'Key': row['Key'],
            'search_string': search_string
        }
        songs.append(song)

    if not songs:
        return f"No songs found for {category_name}: {original_subcategory}.", 404

    return render_template('songs.html', category=category_name, subcategory=original_subcategory, songs=songs)

@app.route('/stats')
def stats():
    top_artists = df.groupby('Main Artist')['Song'].nunique().sort_values(ascending=False).head(25).reset_index()
    top_countries = df.explode('Country').groupby('Country')['Song'].count().sort_values(ascending=False).head(25).reset_index()
    top_genres = df.explode('Genre').groupby('Genre')['Song'].count().sort_values(ascending=False).head(25).reset_index()
    top_keys = df.groupby('Key')['Song'].count().sort_values(ascending=False).head(25).reset_index()
    top_bpms = df.groupby('BPM')['Song'].count().sort_values(ascending=False).head(25).reset_index()
    top_bpm_ranges = df.groupby('BPM Range')['Song'].count().sort_values(ascending=False).head(25).reset_index()
    top_years = df.groupby('Year Released')['Song'].count().sort_values(ascending=False).head(25).reset_index()
    top_decades = df.groupby('Year Range')['Song'].count().sort_values(ascending=False).head(25).reset_index()
    top_languages = df.explode('Language').groupby('Language')['Song'].count().sort_values(ascending=False).head(25).reset_index()

    # Format BPM Range as "90-99", "100-109", etc.
    top_bpm_ranges['BPM Range'] = top_bpm_ranges['BPM Range'].apply(lambda x: f"{x}-{x + 9}")

    stats_data = {
        'Artists': top_artists.to_dict('records'),
        'Countries': top_countries.to_dict('records'),
        'Genres': top_genres.to_dict('records'),
        'Keys': top_keys.to_dict('records'),
        'BPMs': top_bpms.to_dict('records'),
        'BPM Ranges': top_bpm_ranges.to_dict('records'),  # Now formatted as "90-99", etc.
        'Year Released': top_years.to_dict('records'),
        'Decades': top_decades.to_dict('records'),
        'Languages': top_languages.to_dict('records'),  # Moved 'Languages' here
    }

    return render_template('stats.html', stats=stats_data)

@app.route('/stats/<stat_category>')
def stats_detail(stat_category):
    stat_category = stat_category.replace('_', ' ').title()
    if stat_category == 'Artists':
        data = df.groupby('Main Artist')['Song'].nunique().sort_values(ascending=False).reset_index()
    elif stat_category == 'Countries':
        data = df.explode('Country').groupby('Country')['Song'].count().sort_values(ascending=False).reset_index()
    elif stat_category == 'Languages':
        data = df.explode('Language').groupby('Language')['Song'].count().sort_values(ascending=False).reset_index()
    elif stat_category == 'Genres':
        data = df.explode('Genre').groupby('Genre')['Song'].count().sort_values(ascending=False).reset_index()
    elif stat_category == 'Keys':
        data = df.groupby('Key')['Song'].count().sort_values(ascending=False).reset_index()
    elif stat_category == 'BPMs':
        data = df.groupby('BPM')['Song'].count().sort_values(ascending=False).reset_index()
    elif stat_category == 'BPM Ranges':
        data = df.groupby('BPM Range')['Song'].count().sort_values(ascending=False).reset_index()
    elif stat_category == 'Year Released':
        data = df.groupby('Year Released')['Song'].count().sort_values(ascending=False).reset_index()
    elif stat_category == 'Decades':
        data = df.groupby('Year Range')['Song'].count().sort_values(ascending=False).reset_index()
    else:
        return "Invalid stat category.", 400

    data = data.to_dict('records')  # Remove the head(25) to include all items

    return render_template('stats_detail.html', category=stat_category, data=data)

def apply_filters(df, filters):
    filtered_df = df.copy()
    for key, values in filters.items():
        if key in ['Country', 'Language', 'Arrangement']:
            filtered_df = filtered_df[filtered_df[key].apply(lambda x: any(item in x for item in values))]
        else:
            filtered_df = filtered_df[filtered_df[key].isin(values)]
    return filtered_df

@app.route('/add_youtube', methods=['GET', 'POST'])
def add_youtube():
    if request.method == 'POST':
        try:
            # Debug print all form data
            print("Form data received:")
            for key, value in request.form.items():
                print(f"{key}: {value}")

            # Get and validate required fields
            youtube_url = request.form.get('youtube_url', '').strip()
            artist = request.form.get('artist', '').strip()
            song_title = request.form.get('song_title', '').strip()
            genre = request.form.get('genre', '').strip()
            language = request.form.get('language', '').strip()
            country = request.form.get('country', '').strip()
            year_str = request.form.get('year', '').strip()
            featuring = request.form.get('featuring', '').strip()

            print(f"Year value received: '{year_str}'")  # Debug print

            # Validate required fields
            if not all([youtube_url, artist, song_title, genre, language, country, year_str]):
                missing_fields = [field for field, value in {
                    'YouTube URL': youtube_url,
                    'Artist': artist,
                    'Song Title': song_title,
                    'Genre': genre,
                    'Language': language,
                    'Country': country,
                    'Year': year_str
                }.items() if not value]
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

            # Validate year
            try:
                if not year_str:
                    raise ValueError("Year is required")
                year = int(year_str)
                if year < 1900 or year > 2024:
                    raise ValueError("Year must be between 1900 and 2024")
            except ValueError as e:
                if "invalid literal for int()" in str(e):
                    raise ValueError(f"Invalid year format: '{year_str}'. Please enter a valid year.")
                raise

            # Download audio
            print(f"Downloading audio from: {youtube_url}")
            temp_file, video_info = download_audio_from_youtube(youtube_url)
            
            try:
                # Extract features
                print("Extracting audio features...")
                features = extract_audio_features(temp_file)
                
                # Create new song entry
                new_song = {
                    'Main Artist': artist,
                    'Song': song_title,
                    'Featuring': featuring,
                    'Duration': features['Duration'],
                    'Year Released': year,
                    'BPM': features['BPM'],
                    'Key': features['Key'],
                    'Genre': genre,
                    'Language': language,
                    'Country': country
                }
                
                print("New song data:", new_song)
                
                # Add to DataFrame
                global df
                df = pd.concat([df, pd.DataFrame([new_song])], ignore_index=True)
                
                # Save updated DataFrame
                print("Saving to CSV...")
                df.to_csv('data/songs.csv', index=False)
                
                return jsonify({
                    'success': True,
                    'message': 'Song added successfully'
                })
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"Cleaned up temporary file: {temp_file}")
            
        except Exception as e:
            print(f"Error processing request: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
            
    return render_template('add_youtube.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)