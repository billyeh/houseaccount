from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.contrib import auth
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'houseaccount.views.login_user'),
    url(r'^login/', 'houseaccount.views.login_user'),
    url(r'^logout/', 'houseaccount.views.logout_user'),
    url(r'^welcome/', 'houseaccount.views.landing_page'),
    url(r'^payments/', 'houseaccount.views.enter_payment'),
    url(r'^create-house-account/', 'houseaccount.views.create_house_account'),
    url(r'^submit-house-account/', 'houseaccount.views.submit_house_account'),
    # url(r'^houseaccount/', include('houseaccount.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
