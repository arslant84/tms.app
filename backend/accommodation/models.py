from django.db import models
from accounts.models import User
from trf.models import TravelRequest

class AccommodationStaffHouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class AccommodationRoom(models.Model):
    staff_house = models.ForeignKey(AccommodationStaffHouse, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    room_type = models.CharField(max_length=255, blank=True, null=True)
    capacity = models.IntegerField(default=1)
    status = models.CharField(max_length=255, default='Available')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class AccommodationRequest(models.Model):
    """
    Accommodation request model
    Status will be set by workflow engine based on configured approval roles
    Examples: "Draft", "Pending HOD", "Pending Line Manager", "Approved", etc.
    """

    # Note: STATUS_CHOICES removed to support dynamic workflow statuses

    requestor_name = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=255, blank=True, null=True)
    cost_center = models.CharField(max_length=255, blank=True, null=True)
    tel_email = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    status = models.CharField(max_length=100, default='Draft', help_text="Dynamic status set by workflow engine")
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    additional_comments = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    additional_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.requestor_name

class AccommodationBooking(models.Model):
    staff_house = models.ForeignKey(AccommodationStaffHouse, on_delete=models.CASCADE)
    room = models.ForeignKey(AccommodationRoom, on_delete=models.CASCADE)
    staff = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    date = models.DateField()
    trf = models.ForeignKey(TravelRequest, on_delete=models.CASCADE, blank=True, null=True)
    status = models.CharField(max_length=255, default='Confirmed')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('room', 'date')

    def __str__(self):
        return f'{self.room} on {self.date}'
