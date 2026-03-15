from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm
from .models import Client, Order
import openai
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm
from .models import Client, Order
from openai import OpenAI
from django.conf import settings

# inicijalizacija OpenAI klijenta
client = OpenAI(api_key=settings.OPENAI_API_KEY)


@login_required
def dashboard(request):
    clients = Client.objects.all()
    orders = Order.objects.all()

    prediction_rows = None
    if request.method == "POST" and "ai_predict" in request.POST:
        selected_ids = request.POST.getlist("selected_orders")
        selected_orders = orders.filter(id__in=selected_ids)

        if selected_orders.exists():
            orders_text = "\n".join([
                f"{o.client.full_name} kupio {o.product_name}"
                for o in selected_orders
            ])
        else:
            orders_text = "Nema selektovanih porudžbina."

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ti si AI analitičar koji predviđa ponašanje klijenata."},
                    {"role": "user", "content": f"Ovo su porudžbine:\n{orders_text}\nPredvidi buduće ponašanje klijenata."}
                ]
            )
            prediction_text = response.choices[0].message.content
            # razbij tekst po linijama da bi se prikazao u tabeli
            prediction_rows = [line.strip() for line in prediction_text.split("\n") if line.strip()]
        except Exception as e:
            prediction_rows = [f"Nema dostupne AI predikcije (greška: {e})"]

    return render(request, "list_crm/dashboard.html", {
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
    return render(request, "list_crm/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            return render(request, "list_crm/login.html", {"error": "Invalid credentials"})
    return render(request, "list_crm/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")




