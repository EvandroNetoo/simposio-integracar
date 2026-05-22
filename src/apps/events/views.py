from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from events.forms import EventForm
from events.models import Event


class EventListView(View):
    def get(self, request: HttpRequest):
        events = Event.objects.all()
        return render(request, 'events/event_list.html', {'events': events})


class EventCreateView(View):
    form_class = EventForm
    template_name = 'events/event_create.html'

    def get(self, request: HttpRequest):
        form = self.form_class()
        context = {'form': form}
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest):
        form = self.form_class(request.POST)
        if not form.is_valid():
            context = {'form': form}
            return render(request, self.template_name, context)
        event: Event = form.save(commit=False)
        event.owner = request.user
        event.save()
        return redirect('event_detail', pk=event.pk)


class EventDetailView(View):
    template_name = 'events/event_detail.html'

    def get(self, request: HttpRequest, pk: int):
        event = get_object_or_404(Event, pk=pk)
        return render(request, self.template_name, {'event': event})
