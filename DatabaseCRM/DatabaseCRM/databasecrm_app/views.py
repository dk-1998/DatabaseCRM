from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .forms import RegisterForm
from .models import Client, Order
from openai import OpenAI
import re

# inicijalizacija OpenAI klijenta
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def clean_markdown(text):
    """Uklanja markdown formatiranje i čisti tekst za prikaz"""
    # Ukloni bold (**text**)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Ukloni italic (*text*)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Ukloni bullet liste (- ili *)
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
    # Ukloni hash za heading
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    return text


def format_prediction_response(prediction_text):
    """Formatira AI odgovor u pregledne redove"""
    lines = prediction_text.split('\n')
    formatted_rows = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Očisti markdown
        line = clean_markdown(line)
        
        # Dodaj ikonice za različite sekcije
        if any(keyword in line.upper() for keyword in ['SUMMARY', 'SAŽETAK', 'PREGLED']):
            formatted_rows.append(f"📊 {line}")
        elif any(keyword in line.upper() for keyword in ['CLIENT', 'KLIJENT']):
            if ':' in line or ' - ' in line:
                formatted_rows.append(f"👤 {line}")
            else:
                formatted_rows.append(f"👥 {line}")
        elif any(keyword in line.upper() for keyword in ['RECOMMENDATION', 'PREPORUKA', 'TOP']):
            formatted_rows.append(f"🎯 {line}")
        elif any(keyword in line.upper() for keyword in ['RISK', 'RIZIK', 'UPOZORENJE']):
            formatted_rows.append(f"⚠️ {line}")
        elif any(keyword in line.upper() for keyword in ['CROSS', 'SELLING', 'PROIZVOD']):
            formatted_rows.append(f"💡 {line}")
        elif line[0].isdigit() and '.' in line[:3]:
            # Numerisane stavke
            formatted_rows.append(f"   {line}")
        elif line.startswith('•') or line.startswith('-'):
            # Bullet points
            formatted_rows.append(f"   {line}")
        else:
            formatted_rows.append(f"   {line}")
    
    # Grupiši po klijentima za bolju preglednost
    final_rows = []
    current_client = None
    
    for row in formatted_rows:
        if '👤' in row or '👥' in row:
            # Dodaj prazan red pre novog klijenta
            if current_client is not None:
                final_rows.append("")
            current_client = row
            final_rows.append(row)
        else:
            final_rows.append(row)
    
    return final_rows


@login_required
def dashboard(request):
    clients = Client.objects.all()
    orders = Order.objects.all().select_related('client').order_by('-created_at')

    prediction_rows = None
    if request.method == "POST" and "ai_predict" in request.POST:
        selected_ids = request.POST.getlist("selected_orders")
        
        if selected_ids:
            selected_orders = orders.filter(id__in=selected_ids)
        else:
            selected_orders = orders  # Ako ništa nije selektovano, analiziraj sve

        if selected_orders.exists():
            # Detaljna analiza po klijentima
            client_data = {}
            for order in selected_orders:
                client_name = order.client.full_name
                if client_name not in client_data:
                    client_data[client_name] = {
                        'products': [],
                        'prices': [],
                        'total_spent': 0,
                        'order_count': 0,
                        'first_order': order.created_at,
                        'last_order': order.created_at,
                        'orders': []
                    }
                
                client_data[client_name]['products'].append(order.product_name)
                client_data[client_name]['prices'].append(float(order.price))
                client_data[client_name]['total_spent'] += float(order.price)
                client_data[client_name]['order_count'] += 1
                client_data[client_name]['orders'].append({
                    'product': order.product_name,
                    'price': float(order.price),
                    'date': order.created_at
                })
                
                # Ažuriraj prvu i poslednju porudžbinu
                if order.created_at < client_data[client_name]['first_order']:
                    client_data[client_name]['first_order'] = order.created_at
                if order.created_at > client_data[client_name]['last_order']:
                    client_data[client_name]['last_order'] = order.created_at
            
            # Formiranje strukturiranog upita za AI
            analysis_text = "ANALIZA KUPACA I PORUDŽBINA\n"
            analysis_text += "=" * 40 + "\n\n"
            
            for idx, (client_name, data) in enumerate(client_data.items(), 1):
                avg_spent = data['total_spent'] / data['order_count']
                
                analysis_text += f"{idx}. KUPAC: {client_name}\n"
                analysis_text += f"   ├─ Broj porudžbina: {data['order_count']}\n"
                analysis_text += f"   ├─ Ukupna potrošnja: {data['total_spent']:.2f} RSD\n"
                analysis_text += f"   ├─ Prosečna vrednost porudžbine: {avg_spent:.2f} RSD\n"
                analysis_text += f"   ├─ Prva porudžbina: {data['first_order'].strftime('%d.%m.%Y')}\n"
                analysis_text += f"   ├─ Poslednja porudžbina: {data['last_order'].strftime('%d.%m.%Y')}\n"
                analysis_text += f"   ├─ Kupljeni proizvodi: {', '.join(set(data['products']))}\n"
                analysis_text += f"   └─ Kategorija: {'⭐ VIP kupac' if data['total_spent'] > 1000 else '◆ Redovan kupac' if data['order_count'] > 2 else '○ Novi kupac'}\n\n"
            
            analysis_text += "\nZAHTEV ZA ANALIZU:\n"
            analysis_text += "Na osnovu gornjih podataka, napravi detaljnu analizu u sledećem formatu:\n\n"
            analysis_text += "SAŽETAK UKUPNIH PODATAKA\n"
            analysis_text += "------------------------\n"
            analysis_text += "[Ovde napiši kratak pregled svih kupaca]\n\n"
            analysis_text += "ANALIZA PO KUPCIMA\n"
            analysis_text += "------------------\n"
            analysis_text += "[Za svakog kupca napiši poseban pasus koji sadrži:\n"
            analysis_text += " Ime kupca: trenutni status, predviđanje buduće potrošnje, konkretna preporuka]\n\n"
            analysis_text += "TOP 3 PREPORUKE\n"
            analysis_text += "---------------\n"
            analysis_text += "[Navedi 3 najvažnije preporuke numerisane 1, 2, 3]\n\n"
            analysis_text += "PROCENA RIZIKA\n"
            analysis_text += "--------------\n"
            analysis_text += "[Navedi kupce koji su u riziku od odlaska i zašto]\n\n"
            analysis_text += "CROSS SELLING PREDLOZI\n"
            analysis_text += "----------------------\n"
            analysis_text += "[Predloži dodatne proizvode za svakog kupca]\n\n"
            analysis_text += "VAŽNO: Ne koristi markdown formatiranje (*, **, #, -). Piši čistim tekstom."
            
        else:
            analysis_text = "Nema dostupnih porudžbina za analizu."

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """Ti si ekspert za CRM analitiku i predviđanje ponašanja kupaca.
                    
                    Pravila formatiranja:
                    1. NE koristi markdown (*, **, __, #, -)
                    2. Piši čistim tekstom, jasno i pregledno
                    3. Koristi velika slova za naslove sekcija
                    4. Za nabrajanje koristi brojeve 1. 2. 3.
                    5. Svaka sekcija treba da bude jasno odvojena praznim redom
                    6. Za svakog kupca daj konkretne, personalizovane preporuke
                    7. Budi precizan i konkretan, bez opštih fraza
                    """},
                    {"role": "user", "content": analysis_text}
                ],
                temperature=0.7,
                max_tokens=1200
            )
            
            prediction_text = response.choices[0].message.content
            prediction_rows = format_prediction_response(prediction_text)
            
            # Dodaj header informaciju
            total_orders_analyzed = selected_orders.count()
            total_clients_analyzed = len(set(selected_orders.values_list('client__full_name', flat=True)))
            
            header_info = [
                f"📊 ANALIZIRANO: {total_orders_analyzed} porudžbina od {total_clients_analyzed} kupaca",
                "═" * 50,
                ""
            ]
            prediction_rows = header_info + prediction_rows
            
        except Exception as e:
            prediction_rows = [
                "❌ GREŠKA PRI AI ANALIZI",
                "═" * 30,
                f"Detalji greške: {str(e)}",
                "",
                "Molimo pokušajte ponovo ili kontaktirajte administratora."
            ]

    return render(request, "databasecrm_app/dashboard.html", {
        "clients": clients,
        "orders": orders,
        "prediction_rows": prediction_rows
    })


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = RegisterForm()
    return render(request, "databasecrm_app/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            return render(request, "databasecrm_app/login.html", {"error": "Invalid credentials"})
    return render(request, "databasecrm_app/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")



