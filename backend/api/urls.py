from django.urls import path
from .views import HistoryView, LatestView, AnalyzeView, ResultView

urlpatterns = [
    path('history',              HistoryView.as_view()),
    path('latest',               LatestView.as_view()),
    path('analyze',              AnalyzeView.as_view()),
    path('result/<str:task_id>', ResultView.as_view()),
]
