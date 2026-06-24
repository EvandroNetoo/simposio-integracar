from django.core.mail import send_mail
from django.db import transaction


def _absolute_url(request, viewname, **kwargs):
    from django.urls import reverse

    return request.build_absolute_uri(reverse(viewname, kwargs=kwargs))


def _send_after_commit(subject, message, recipients):
    recipients = sorted({
        email.strip().lower()
        for email in recipients
        if email and email.strip()
    })
    if not recipients:
        return
    transaction.on_commit(
        lambda: send_mail(
            subject,
            message,
            None,
            recipients,
            fail_silently=True,
        )
    )


def get_paper_author_emails(paper):
    emails = {paper.user.email}
    for coauthor in paper.coauthors.select_related('user'):
        if coauthor.user_id:
            emails.add(coauthor.user.email)
        elif coauthor.email:
            emails.add(coauthor.email)
    return emails


def get_event_committee_emails(event):
    emails = set()
    if event.owner_id and event.owner.email:
        emails.add(event.owner.email)
    for member in event.committee_members.select_related('user'):
        if member.is_manager and member.user.email:
            emails.add(member.user.email)
    if event.contact_email:
        emails.add(event.contact_email)
    return emails


def notify_reviewers_assigned(request, assignments):
    for assignment in assignments:
        paper = assignment.paper
        event = paper.event
        paper_url = _absolute_url(
            request,
            'review_detail',
            pk=assignment.pk,
        )
        _send_after_commit(
            f'Novo trabalho para avaliar - {event.name}',
            (
                f'Voce recebeu um trabalho para avaliar no evento {event}.\n\n'
                f'Trabalho: {paper.title}\n'
                f'Eixo tematico: {paper.eixo_tematico.name}\n'
                f'Prazo: {event.evaluation_period_end:%d/%m/%Y %H:%M}\n\n'
                f'Acesse o parecer: {paper_url}'
            ),
            [assignment.reviewer.user.email],
        )


def notify_review_published(request, review, *, updated=False):
    paper = review.assignment.paper
    event = paper.event
    paper_url = _absolute_url(request, 'paper_detail', pk=paper.pk)
    status = 'atualizado' if updated else 'publicado'
    _send_after_commit(
        f'Parecer {status} - {paper.title}',
        (
            f'Um parecer foi {status} para o seu trabalho no evento {event}.\n\n'
            f'Trabalho: {paper.title}\n'
            f'Recomendacao: {review.get_recommendation_display()}\n\n'
            f'Comentarios ao autor:\n{review.comments_to_author}\n\n'
            f'Acesse o sistema para acompanhar: {paper_url}'
        ),
        get_paper_author_emails(paper),
    )


def notify_final_decision_published(request, decision):
    paper = decision.paper
    paper_url = _absolute_url(request, 'paper_detail', pk=paper.pk)
    _send_after_commit(
        f'Decisao final publicada - {paper.title}',
        (
            f'A decisao final do seu trabalho foi publicada.\n\n'
            f'Trabalho: {paper.title}\n'
            f'Resultado: {decision.get_result_display()}\n\n'
            f'Justificativa:\n{decision.justification}\n\n'
            f'Acesse o sistema para acompanhar: {paper_url}'
        ),
        get_paper_author_emails(paper),
    )


def notify_submission_received(request, submission, *, correction=False):
    paper = submission.paper
    event = paper.event
    paper_url = _absolute_url(request, 'paper_detail', pk=paper.pk)
    kind = 'correcao enviada' if correction else 'nova submissao'
    _send_after_commit(
        f'{kind.title()} - {event.name}',
        (
            f'O evento {event} recebeu uma {kind}.\n\n'
            f'Trabalho: {paper.title}\n'
            f'Autor principal: {paper.user.full_name or paper.user.email}\n'
            f'Eixo tematico: {paper.eixo_tematico.name}\n'
            f'Versao: {submission.version}\n\n'
            f'Acesse o trabalho: {paper_url}'
        ),
        get_event_committee_emails(event),
    )
