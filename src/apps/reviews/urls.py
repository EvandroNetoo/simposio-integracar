from django.urls import path

from reviews import views

urlpatterns = [
    path(
        'avaliacoes/',
        views.ReviewerDashboardView.as_view(),
        name='reviewer_dashboard',
    ),
    path(
        'avaliacoes/<int:pk>/',
        views.ReviewDetailView.as_view(),
        name='review_detail',
    ),
    path(
        'eventos/<int:event_pk>/comissao/',
        views.CommitteeDashboardView.as_view(),
        name='committee_dashboard',
    ),
    path(
        'eventos/<int:event_pk>/comissao/membros/',
        views.CommitteeMemberCreateView.as_view(),
        name='committee_member_create',
    ),
    path(
        'eventos/<int:event_pk>/comissao/avaliadores/',
        views.ReviewerCreateView.as_view(),
        name='reviewer_create',
    ),
    path(
        'trabalhos/<int:paper_pk>/avaliadores/',
        views.PaperAssignmentManageView.as_view(),
        name='paper_assignment_manage',
    ),
    path(
        'trabalhos/<int:paper_pk>/decisao/',
        views.FinalDecisionCreateView.as_view(),
        name='final_decision_create',
    ),
    path(
        'submissoes/<int:pk>/arquivo/',
        views.SubmissionDownloadView.as_view(),
        name='submission_download',
    ),
]
