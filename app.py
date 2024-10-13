from flask import Flask, render_template, request
import pandas as pd
from rapidfuzz import process
from unicodedata import normalize
from urllib.parse import unquote
import html

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

@app.route('/test')
def test():
    return 'Flask is working!'

@app.route('/')
def home():
    categories = ['Key', 'BPM', 'Genre', 'Language', 'Country', 'Year Released', 'Arrangement']
    
    # Prepare all songs data
    songs = []
    for _, row in df.iterrows():
        featuring = row['Featuring']
        if pd.isna(featuring):
            featuring = ''
        else:
            featuring = str(featuring).strip()

        search_terms = []
        for col in ['Main Artist', 'Song', 'Featuring', 'Key']:
            normalized_col = col + '_normalized'
            value = row.get(normalized_col, '')
            if pd.notnull(value):
                search_terms.append(str(value))
            else:
                search_terms.append('')
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
    subcategory_value = unquote(subcategory_value).lower().strip()

    if category_name == 'BPM':
        bpm_range = int(subcategory_value)
        filtered_df = df[df['BPM Range'] == bpm_range]
    elif category_name == 'Year Released':
        year_range = int(subcategory_value)
        filtered_df = df[df['Year Range'] == year_range]
    elif category_name in ['Country', 'Language', 'Arrangement', 'Genre']:
        filtered_df = df[df[category_name + '_normalized'].apply(lambda x: subcategory_value in x)]
    else:
        filtered_df = df[df[category_name + '_normalized'] == subcategory_value]

    # Prepare songs data
    songs = []
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
            if pd.notnull(value):
                search_terms.append(str(value))
            else:
                search_terms.append('')
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

    return render_template('songs.html', category=category_name, subcategory=subcategory_value, songs=songs)

def apply_filters(df, filters):
    filtered_df = df.copy()
    for key, values in filters.items():
        if key in ['Country', 'Language', 'Arrangement']:
            filtered_df = filtered_df[filtered_df[key].apply(lambda x: any(item in x for item in values))]
        else:
            filtered_df = filtered_df[filtered_df[key].isin(values)]
    return filtered_df

if __name__ == '__main__':
    app.run(debug=True)