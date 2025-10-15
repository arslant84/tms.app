from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ExpenseClaim, ExpenseItem, ClaimsApprovalStep, ExpenseStatus, ExpenseCategory
from trf.models import TravelRequest

User = get_user_model()


class ExpenseItemSerializer(serializers.ModelSerializer):
    """Serializer for Expense Items"""

    class Meta:
        model = ExpenseItem
        fields = ['id', 'description', 'amount', 'category', 'date', 'receipt_url']
        read_only_fields = ['id']

    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value


class ClaimsApprovalStepSerializer(serializers.ModelSerializer):
    """Serializer for Claims Approval Steps"""

    class Meta:
        model = ClaimsApprovalStep
        fields = [
            'id', 'claim', 'step_role', 'step_name', 'status',
            'step_date', 'comments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_status(self, value):
        """Validate approval status"""
        valid_statuses = ['Not Started', 'Pending', 'Approved', 'Rejected', 'In Review']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value


class ExpenseClaimSerializer(serializers.ModelSerializer):
    """Main serializer for Expense Claims (list view)"""
    items = ExpenseItemSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    trf_reference = serializers.CharField(source='trf.id', read_only=True)

    class Meta:
        model = ExpenseClaim
        fields = [
            'id', 'user', 'user_name', 'user_id', 'trf', 'trf_reference', 'trf_id',
            'title', 'description', 'total_amount', 'currency', 'expense_date',
            'category', 'status', 'receipt_urls', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['id', 'user_id', 'trf_id', 'created_at', 'updated_at']

    def validate_status(self, value):
        """Validate expense claim status"""
        if value not in ExpenseStatus.values:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(ExpenseStatus.values)}"
            )
        return value

    def validate_category(self, value):
        """Validate expense category"""
        if value not in ExpenseCategory.values:
            raise serializers.ValidationError(
                f"Category must be one of: {', '.join(ExpenseCategory.values)}"
            )
        return value


class ExpenseClaimDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Expense Claims with nested data"""
    items = ExpenseItemSerializer(many=True, read_only=True)
    approval_steps = ClaimsApprovalStepSerializer(
        many=True, read_only=True, source='claimsapprovalstep_set'
    )
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    trf_reference = serializers.CharField(source='trf.id', read_only=True)

    class Meta:
        model = ExpenseClaim
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_id', 'trf',
            'trf_reference', 'trf_id', 'title', 'description', 'total_amount',
            'currency', 'expense_date', 'category', 'status', 'receipt_urls',
            'created_at', 'updated_at', 'items', 'approval_steps'
        ]
        read_only_fields = ['id', 'user_id', 'trf_id', 'created_at', 'updated_at']


class ExpenseClaimCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Expense Claims"""
    items = ExpenseItemSerializer(many=True, required=True)

    class Meta:
        model = ExpenseClaim
        fields = [
            'trf', 'title', 'description', 'total_amount', 'currency',
            'expense_date', 'category', 'receipt_urls', 'items'
        ]

    def validate_items(self, value):
        """Ensure at least one item exists"""
        if not value:
            raise serializers.ValidationError("At least one expense item is required")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user

        # Create expense claim
        expense_claim = ExpenseClaim.objects.create(
            user=user,
            status=ExpenseStatus.DRAFT,
            **validated_data
        )

        # Create expense items
        for item_data in items_data:
            item = ExpenseItem.objects.create(**item_data)
            expense_claim.items.add(item)

        return expense_claim


class ExpenseClaimUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating Expense Claims"""
    items = ExpenseItemSerializer(many=True, required=False)

    class Meta:
        model = ExpenseClaim
        fields = [
            'title', 'description', 'total_amount', 'currency',
            'expense_date', 'category', 'receipt_urls', 'items'
        ]

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        if instance and instance.status not in [ExpenseStatus.DRAFT, ExpenseStatus.REJECTED]:
            raise serializers.ValidationError(
                "Only draft or rejected expense claims can be updated."
            )
        return attrs

    def update(self, instance, validated_data):
        if 'items' in validated_data:
            items_data = validated_data.pop('items')

            # Clear existing items
            instance.items.clear()

            # Add new items
            for item_data in items_data:
                item = ExpenseItem.objects.create(**item_data)
                instance.items.add(item)

        # Update the expense claim fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class ApprovalActionSerializer(serializers.Serializer):
    """Serializer for approval actions (approve/reject)"""
    comments = serializers.CharField(required=False, allow_blank=True)
    step_role = serializers.CharField(required=True)

    def validate_step_role(self, value):
        """Validate step role"""
        valid_roles = [
            'Department Focal', 'HOD', 'Finance', 'Director', 'Country Director'
        ]
        if value not in valid_roles:
            raise serializers.ValidationError(
                f"Step role must be one of: {', '.join(valid_roles)}"
            )
        return value
