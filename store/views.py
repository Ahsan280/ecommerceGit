from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from carts.models import CartItem
from carts.views import _cart_id
from .Forms import ReviewForm
from .models import Product, ReviewRating, ProductGallery
from category.models import Category
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from orders.models import OrderProduct
# Create your views here.
def store(request, category_slug=None):
    categories=None
    products=None
    if category_slug is not None:
        categories=get_object_or_404(Category, slug=category_slug)
        products=Product.objects.filter(category=categories, is_available=True)
        paginator = Paginator(products, 1)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count=products.count()
    else:
        products=Product.objects.all().filter(is_available=True).order_by('created_date')
        paginator=Paginator(products, 3)
        page=request.GET.get('page')
        paged_products=paginator.get_page(page)
        product_count=products.count()

    return render(request, "store/store.html", context={'products':paged_products,
                                                        'product_count':product_count})

def product_details(request, category_slug, product_slug):
    category=get_object_or_404(Category, slug=category_slug)
    product=Product.objects.get(category=category, slug=product_slug)
    in_cart=CartItem.objects.filter(cart__cart_id=_cart_id(request), product=product).exists()
    if request.user.is_authenticated:
        try:
            orderproduct=OrderProduct.objects.filter(user=request.user, product_id=product.id).exists()
        except OrderProduct.DoesNotExist:
            orderproduct=None
    else:
        orderproduct = None
    reviews=ReviewRating.objects.filter(product_id=product.id, status=True)
    product_gallery=ProductGallery.objects.filter(product_id=product.id)

    return render(request, 'store/product_details.html', context={'product': product,
                                                                  'in_cart': in_cart,
                                                                  'orderproduct':orderproduct,
                                                                  'reviews':reviews,
                                                                  'product_gallery':product_gallery})

def search(request):
    if "keyword" in request.GET:
        keyword=request.GET['keyword']
        if keyword:
            products=Product.objects.order_by('created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count=products.count()

    return render(request, "store/store.html", context={'products':products,
                                                        'product_count':product_count})

def submit_review(request, product_id):
    url=request.META.get('HTTP_REFERER')
    if request.method=="POST":
        try:
            reviews=ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form= ReviewForm(request.POST, instance=reviews)
            form.save()
            messages.success(request, 'Thank you! Your review has been updated')
            return redirect(url)
        except ReviewRating.DoesNotExist:
            form=ReviewForm(request.POST)
            if form.is_valid():
                data=ReviewRating()
                data.subject=form.cleaned_data['subject']
                data.rating=form.cleaned_data['rating']
                data.review=form.cleaned_data['review']
                data.ip=request.META.get('REMOTE_ADDR')
                data.product_id=product_id
                data.user_id=request.user.id
                data.save()
                messages.success(request, "Thank you! your review has been submitted")
                return redirect(url)