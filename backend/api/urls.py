from django.urls import path
from .views import HistoryView, LatestView

urlpatterns = [
    path('history', HistoryView.as_view()),
    path('latest', LatestView.as_view()),
]
