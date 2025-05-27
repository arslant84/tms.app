from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ExpenseClaim, ExpenseItem, ExpenseApproval, ExpenseStatus, ExpenseCategory
from trf.models import TravelRequestForm, ApprovalStatus

User = get_user_model()


class ExpenseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseItem
        fields = ['id', 'description', 'amount', 'category', 'date', 'receipt_url']
        read_only_fields = ['id']


class ExpenseApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.ReadOnlyField()
    approver_id = serializers.ReadOnlyField()
    
    class Meta:
        model = ExpenseApproval
        fields = ['id', 'approver', 'approver_name', 'approver_id', 'status', 'comments', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class ExpenseClaimSerializer(serializers.ModelSerializer):
    items = ExpenseItemSerializer(many=True, read_only=False)
    approval_chain = ExpenseApprovalSerializer(many=True, read_only=True)
    user_id = serializers.ReadOnlyField()
    trf_id = serializers.ReadOnlyField()
    
    class Meta:
        model = ExpenseClaim
        fields = [
            'id', 'user', 'user_id', 'trf', 'trf_id', 'title', 'description',
            'total_amount', 'currency', 'expense_date', 'category', 'status',
            'receipt_urls', 'created_at', 'updated_at', 'items', 'approval_chain'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        expense_claim = ExpenseClaim.objects.create(**validated_data)
        
        for item_data in items_data:
            ExpenseItem.objects.create(**item_data, expense_claim=expense_claim)
        
        return expense_claim
    
    def update(self, instance, validated_data):
        if 'items' in validated_data:
            items_data = validated_data.pop('items')
            
            # Delete existing items
            instance.items.all().delete()
            
            # Create new items
            for item_data in items_data:
                ExpenseItem.objects.create(**item_data, expense_claim=instance)
        
        # Update the expense claim fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class ExpenseClaimCreateSerializer(serializers.ModelSerializer):
    items = ExpenseItemSerializer(many=True, required=True)
    
    class Meta:
        model = ExpenseClaim
        fields = [
            'trf', 'title', 'description', 'total_amount', 'currency',
            'expense_date', 'category', 'receipt_urls', 'items'
        ]
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        
        expense_claim = ExpenseClaim.objects.create(
            user=user,
            status=ExpenseStatus.DRAFT,
            **validated_data
        )
        
        for item_data in items_data:
            item = ExpenseItem.objects.create(**item_data)
            expense_claim.items.add(item)
        
        return expense_claim


class ExpenseClaimUpdateSerializer(serializers.ModelSerializer):
    items = ExpenseItemSerializer(many=True, required=False)
    
    class Meta:
        model = ExpenseClaim
        fields = [
            'title', 'description', 'total_amount', 'currency',
            'expense_date', 'category', 'receipt_urls', 'items'
        ]
    
    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        if instance and instance.status != ExpenseStatus.DRAFT:
            raise serializers.ValidationError("Only draft expense claims can be updated.")
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


class ExpenseApprovalActionSerializer(serializers.Serializer):
    comments = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        request = self.context.get('request')
        view = self.context.get('view')
        expense = view.get_object()
        
        # Check if the user is in the approval chain
        approval_step = expense.approval_chain.filter(approver=request.user).first()
        if not approval_step:
            raise serializers.ValidationError("You are not in the approval chain for this expense claim.")
        
        # Check if the approval step is pending
        if approval_step.status != ApprovalStatus.PENDING:
            raise serializers.ValidationError("This expense claim has already been processed by you.")
        
        return attrs
