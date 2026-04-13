import pandas as pd
import random
from flask import Flask, render_template, request, redirect, url_for
import os
from datetime import datetime

df = pd.read_csv("Pokemon.csv")
df['name'] = df['name'].astype(str).str.strip()
df.fillna('', inplace=True)

file_for_revies = "reviews.csv"
if not os.path.exists(file_for_revies):
    pd.DataFrame(columns=['pokemon_name', 'review_text', 'rating', 'timestamp']).to_csv(file_for_revies, index=False)

def load_reviews():
    return pd.read_csv(file_for_revies)

def save_review(pokemon_name, review_text, rating):
    reviews = load_reviews()
    new_review = pd.DataFrame([{
        'pokemon_name': pokemon_name,
        'review_text': review_text,
        'rating': rating,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    reviews = pd.concat([reviews, new_review], ignore_index=True)
    reviews.to_csv(file_for_revies, index=False)


def recommend(query: str, top_k: int = 5):
    query = query.lower()
    scores = []

    if len(query) < 3 or query in ["покемон", "pokemon", "выбери", "кого", "случайный"]:
        for _, row in df.iterrows():
            score = row['attack'] * 0.2 + row['speed'] * 0.2 + row['hp'] * 0.2 + random.uniform(0, 10)
            scores.append((row['name'], score))
    else:
        for _, row in df.iterrows():
            score = 0
            # Типы
            if any(word in query for word in ['огонь', 'fire', 'огненный']):
                if row['type1'] == 'fire' or row['type2'] == 'fire':
                    score += 40
            if any(word in query for word in ['вода', 'water', 'водный']):
                if row['type1'] == 'water' or row['type2'] == 'water':
                    score += 40
            if any(word in query for word in ['трава', 'grass', 'травяной']):
                if row['type1'] == 'grass' or row['type2'] == 'grass':
                    score += 40
            if any(word in query for word in ['электричество', 'electric', 'электрический']):
                if row['type1'] == 'electric' or row['type2'] == 'electric':
                    score += 40
            if any(word in query for word in ['псих', 'psychic', 'психический']):
                if row['type1'] == 'psychic' or row['type2'] == 'psychic':
                    score += 40
            if any(word in query for word in ['дракон', 'dragon']):
                if row['type1'] == 'dragon' or row['type2'] == 'dragon':
                    score += 50


            if any(word in query for word in ['сильный', 'strong', 'мощный']):
                score += row['attack'] * 0.4 + row['sp_attack'] * 0.2
            if any(word in query for word in ['быстрый', 'fast', 'скоростной']):
                score += row['speed'] * 0.6
            if any(word in query for word in ['живучий', 'tank', 'выносливый']):
                score += row['hp'] * 0.4 + row['defense'] * 0.2 + row['sp_defense'] * 0.1
            if any(word in query for word in ['умный', 'smart', 'интеллектуальный']):
                score += row['sp_attack'] * 0.5

            if score == 0:
                score = row['attack'] * 0.1 + row['speed'] * 0.1 + row['hp'] * 0.05

            score += random.uniform(0, 5)
            scores.append((row['name'], score))

    if not scores:
        return []
    max_score = max(score for _, score in scores)
    results = []
    for name, score in scores:
        percent = (score / max_score) * 100 if max_score > 0 else 0
        results.append((name, score, percent))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def search_by_name(name_query):
    name_query = name_query.lower().strip()
    if not name_query:
        return []
    result = df[df['name'].str.lower().str.contains(name_query)]
    return result.to_dict('records')


def get_weakest_top(n=5):
    df_copy = df.copy()
    stats_cols = ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']
    df_copy['total'] = df_copy[stats_cols].sum(axis=1)
    weakest = df_copy.nsmallest(n, 'total')
    return weakest.to_dict('records')


def search_by_stat_range(stat_name, min_val, max_val):
    if stat_name not in df.columns:
        return []
    filtered = df[(df[stat_name] >= min_val) & (df[stat_name] <= max_val)]
    return filtered.to_dict('records')


def get_review_stats():
    reviews = load_reviews()
    if reviews.empty:
        return pd.DataFrame(columns=['pokemon_name', 'avg_rating', 'num_reviews'])
    stats = reviews.groupby('pokemon_name')['rating'].agg(['mean', 'count']).reset_index()
    stats.columns = ['pokemon_name', 'avg_rating', 'num_reviews']
    stats['avg_rating'] = stats['avg_rating'].round(2)
    return stats


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend_route():
    query = request.form.get('query', '')
    results = recommend(query, 5)
    pokemons = []
    for name, score, percent in results:
        pokemon = df[df['name'] == name].iloc[0].to_dict()
        pokemon['score'] = round(score, 1)
        pokemon['compatibility'] = round(percent, 1)
        pokemons.append(pokemon)
    return render_template('recommend.html', query=query, pokemons=pokemons)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        name = request.form.get('name', '')
        results = search_by_name(name)
        return render_template('search.html', results=results, search_name=name)
    return render_template('search.html', results=None, search_name='')

@app.route('/weakest')
def weakest():
    weakest_pokemons = get_weakest_top(10)
    return render_template('weakest.html', pokemons=weakest_pokemons)

@app.route('/range', methods=['GET', 'POST'])
def stat_range():
    if request.method == 'POST':
        stat = request.form.get('stat')
        min_val = request.form.get('min_val', type=float)
        max_val = request.form.get('max_val', type=float)
        if stat and min_val is not None and max_val is not None:
            results = search_by_stat_range(stat, min_val, max_val)
            return render_template('range.html', results=results, stat=stat, min_val=min_val, max_val=max_val)
    return render_template('range.html', results=None, stat=None, min_val=None, max_val=None)

@app.route('/review', methods=['GET', 'POST'])
def add_review():
    if request.method == 'POST':
        pokemon_name = request.form.get('pokemon_name', '').strip()
        review_text = request.form.get('review_text', '').strip()
        rating = request.form.get('rating', type=int)
        if pokemon_name and review_text and rating:
            if pokemon_name in df['name'].values:
                save_review(pokemon_name, review_text, rating)
                return redirect(url_for('review_stats'))
            else:
                error = f"Покемон '{pokemon_name}' не найден."
                return render_template('review.html', error=error)
    return render_template('review.html', error=None)

@app.route('/stats')
def review_stats():
    stats = get_review_stats()
    enriched = []
    for _, row in stats.iterrows():
        pokemon_data = df[df['name'] == row['pokemon_name']]
        if not pokemon_data.empty:
            p = pokemon_data.iloc[0].to_dict()
            p['avg_rating'] = row['avg_rating']
            p['num_reviews'] = row['num_reviews']
            enriched.append(p)
    return render_template('stats.html', stats=enriched)

if __name__ == '__main__':
    app.run(debug=True)