from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Invoice


@login_required
def invoice_download(request, order_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("order", "order__user").prefetch_related("order__items"),
        order_id=order_id,
    )
    order = invoice.order
    if not (request.user.is_staff or order.user_id == request.user.id):
        return HttpResponse(status=404)

    response = render(request, "store/invoice.html", {"invoice": invoice, "order": order})
    response["Content-Disposition"] = f'inline; filename="{invoice.number}.html"'
    return response

# Create your views here.
