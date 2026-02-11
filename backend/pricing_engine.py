"""
Pricing Engine and Business Rules
Handles all pricing calculations, capacity checks, and policy enforcement
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Default settings (can be overridden by SystemSettings)
DEFAULT_DEPOSIT_PERCENTAGE = 50.0
DEFAULT_TAX_RATE = 0.0
DEFAULT_ROOMS_CAPACITY = 7
DEFAULT_CRATES_CAPACITY = 4


class PricingEngine:
    """
    Server-side pricing calculation engine.
    All business rules are enforced here, never in frontend.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def get_system_setting(self, key: str, default: Any = None) -> Any:
        """Get a system setting value"""
        setting = await self.db.system_settings.find_one({"key": key}, {"_id": 0})
        if not setting:
            return default
        
        value = setting.get('value')
        value_type = setting.get('value_type', 'string')
        
        if value_type == 'number':
            return float(value)
        elif value_type == 'boolean':
            return value.lower() in ('true', '1', 'yes')
        elif value_type == 'json':
            import json
            return json.loads(value)
        return value
    
    async def get_service_type(self, service_type_id: str) -> Optional[Dict]:
        """Get service type by ID"""
        return await self.db.service_types.find_one({"id": service_type_id, "active": True}, {"_id": 0})
    
    async def get_active_add_ons(self, location_id: str = None, service_type_id: str = None) -> List[Dict]:
        """Get active add-ons, optionally filtered by location and service type"""
        query = {"active": True}
        if location_id:
            query["$or"] = [{"location_id": None}, {"location_id": location_id}]
        
        add_ons = await self.db.add_ons.find(query, {"_id": 0}).sort("sort_order", 1).to_list(100)
        
        # Filter by service type if specified
        if service_type_id:
            add_ons = [
                a for a in add_ons 
                if not a.get('service_type_ids') or service_type_id in a.get('service_type_ids', [])
            ]
        
        return add_ons
    
    async def get_pricing_rules(self, location_id: str, service_type_id: str, check_in: datetime, check_out: datetime) -> List[Dict]:
        """Get applicable pricing rules for the date range"""
        rules = await self.db.pricing_rules.find({"active": True}, {"_id": 0}).sort("priority", 1).to_list(100)
        
        applicable = []
        for rule in rules:
            # Check location
            if rule.get('location_id') and rule['location_id'] != location_id:
                continue
            
            # Check service type
            if rule.get('service_type_ids') and service_type_id not in rule.get('service_type_ids', []):
                continue
            
            # Check date range
            rule_type = rule.get('rule_type')
            
            if rule_type == 'weekend':
                # Weekend rules apply if any day in range is a weekend
                applicable.append(rule)
            
            elif rule_type in ('holiday', 'seasonal', 'blackout'):
                rule_start = rule.get('start_date')
                rule_end = rule.get('end_date')
                
                if rule_start and rule_end:
                    if isinstance(rule_start, str):
                        rule_start = datetime.fromisoformat(rule_start.replace('Z', '+00:00'))
                    if isinstance(rule_end, str):
                        rule_end = datetime.fromisoformat(rule_end.replace('Z', '+00:00'))
                    
                    # Check if booking overlaps with rule dates
                    recurring = rule.get('recurring_yearly', False)
                    if recurring:
                        # Check same month/day across years
                        current = check_in
                        while current < check_out:
                            if (rule_start.month, rule_start.day) <= (current.month, current.day) <= (rule_end.month, rule_end.day):
                                applicable.append(rule)
                                break
                            current += timedelta(days=1)
                    else:
                        # Check exact date overlap
                        if not (check_out <= rule_start or check_in >= rule_end):
                            applicable.append(rule)
        
        return applicable
    
    async def get_capacity_rules(self, location_id: str, service_type_id: str = None) -> List[Dict]:
        """Get capacity rules for a location"""
        query = {"location_id": location_id, "active": True}
        rules = await self.db.capacity_rules.find(query, {"_id": 0}).to_list(100)
        
        if service_type_id:
            rules = [r for r in rules if not r.get('service_type_id') or r['service_type_id'] == service_type_id]
        
        return rules
    
    async def check_capacity(
        self, 
        location_id: str, 
        check_in: datetime, 
        check_out: datetime,
        accommodation_type: str,
        dog_count: int,
        exclude_booking_id: str = None
    ) -> Tuple[bool, bool, int]:
        """
        Check if capacity is available.
        Returns: (is_available, requires_approval, available_spots)
        
        SOFT CAPACITY: Bookings are allowed even if over capacity, but require approval.
        """
        # Get capacity rules
        rules = await self.get_capacity_rules(location_id)
        
        # Find applicable rule
        max_capacity = DEFAULT_ROOMS_CAPACITY if accommodation_type == 'room' else DEFAULT_CRATES_CAPACITY
        buffer_capacity = 0
        
        for rule in rules:
            if rule.get('accommodation_type') == accommodation_type or not rule.get('accommodation_type'):
                max_capacity = rule.get('max_capacity', max_capacity)
                buffer_capacity = rule.get('buffer_capacity', 0)
                break
        
        # Count existing bookings
        query = {
            "location_id": location_id,
            "status": {"$in": ["confirmed", "checked_in", "pending"]},
            "accommodation_type": accommodation_type,
            "$or": [
                {"check_in_date": {"$lt": check_out.isoformat()}, "check_out_date": {"$gt": check_in.isoformat()}}
            ]
        }
        
        if exclude_booking_id:
            query["id"] = {"$ne": exclude_booking_id}
        
        existing_bookings = await self.db.bookings.find(query, {"_id": 0, "dog_ids": 1}).to_list(1000)
        
        # Count dogs already booked
        booked_dogs = sum(len(b.get('dog_ids', [])) for b in existing_bookings)
        
        available_spots = max_capacity - booked_dogs
        total_with_buffer = max_capacity + buffer_capacity
        available_with_buffer = total_with_buffer - booked_dogs
        
        if available_spots >= dog_count:
            # Under regular capacity
            return True, False, available_spots
        elif available_with_buffer >= dog_count:
            # Over regular capacity but within buffer - requires approval
            return True, True, available_with_buffer
        else:
            # Over total capacity - still allowed but requires approval (soft capacity)
            return True, True, available_with_buffer
    
    async def check_blackout_dates(self, location_id: str, check_in: datetime, check_out: datetime) -> List[str]:
        """Check for blackout dates in the range"""
        rules = await self.db.pricing_rules.find({
            "active": True,
            "rule_type": "blackout",
            "$or": [{"location_id": None}, {"location_id": location_id}]
        }, {"_id": 0}).to_list(100)
        
        blocked_dates = []
        
        for rule in rules:
            rule_start = rule.get('start_date')
            rule_end = rule.get('end_date')
            
            if rule_start and rule_end:
                if isinstance(rule_start, str):
                    rule_start = datetime.fromisoformat(rule_start.replace('Z', '+00:00'))
                if isinstance(rule_end, str):
                    rule_end = datetime.fromisoformat(rule_end.replace('Z', '+00:00'))
                
                recurring = rule.get('recurring_yearly', False)
                current = check_in
                
                while current < check_out:
                    if recurring:
                        if (rule_start.month, rule_start.day) <= (current.month, current.day) <= (rule_end.month, rule_end.day):
                            blocked_dates.append(current.strftime('%Y-%m-%d'))
                    else:
                        if rule_start.date() <= current.date() <= rule_end.date():
                            blocked_dates.append(current.strftime('%Y-%m-%d'))
                    current += timedelta(days=1)
        
        return list(set(blocked_dates))
    
    async def calculate_price(
        self,
        service_type_id: str,
        location_id: str,
        dog_ids: List[str],
        check_in: datetime,
        check_out: datetime,
        accommodation_type: str = "room",
        add_on_ids: List[str] = None,
        add_on_quantities: Dict[str, int] = None,
        promo_code: str = None,
        exclude_booking_id: str = None
    ) -> Dict[str, Any]:
        """
        Calculate complete price breakdown for a booking.
        This is the authoritative pricing logic - frontend must use this.
        """
        add_on_ids = add_on_ids or []
        add_on_quantities = add_on_quantities or {}
        
        # Get service type
        service_type = await self.get_service_type(service_type_id)
        if not service_type:
            # Fallback to default pricing if no service type
            service_type = {
                "name": "Standard Boarding",
                "base_price": 50.0,
                "price_type": "per_dog_per_day"
            }
        
        # Calculate nights
        nights = (check_out - check_in).days
        if nights <= 0:
            raise ValueError("Invalid date range")
        
        dog_count = len(dog_ids)
        
        # Base service calculation
        base_price = service_type.get('base_price', 50.0)
        price_type = service_type.get('price_type', 'per_dog_per_day')
        
        if price_type == 'per_dog_per_day':
            service_subtotal = base_price * nights * dog_count
        elif price_type == 'per_day':
            service_subtotal = base_price * nights
        elif price_type == 'per_dog':
            service_subtotal = base_price * dog_count
        else:  # flat
            service_subtotal = base_price
        
        # Add-ons calculation
        add_ons_subtotal = 0.0
        add_ons_detail = []
        
        if add_on_ids:
            available_add_ons = await self.get_active_add_ons(location_id, service_type_id)
            add_on_map = {a['id']: a for a in available_add_ons}
            
            for add_on_id in add_on_ids:
                add_on = add_on_map.get(add_on_id)
                if not add_on:
                    continue
                
                quantity = add_on_quantities.get(add_on_id, 1)
                max_qty = add_on.get('max_quantity', 1)
                quantity = min(quantity, max_qty)
                
                add_on_price = add_on.get('price', 0)
                add_on_price_type = add_on.get('price_type', 'flat')
                
                if add_on_price_type == 'per_dog_per_day':
                    total_add_on = add_on_price * nights * dog_count * quantity
                elif add_on_price_type == 'per_day':
                    total_add_on = add_on_price * nights * quantity
                elif add_on_price_type == 'per_dog':
                    total_add_on = add_on_price * dog_count * quantity
                else:  # flat
                    total_add_on = add_on_price * quantity
                
                add_ons_subtotal += total_add_on
                add_ons_detail.append({
                    "add_on_id": add_on_id,
                    "name": add_on.get('name'),
                    "quantity": quantity,
                    "unit_price": add_on_price,
                    "price_type": add_on_price_type,
                    "total": total_add_on
                })
        
        # Apply pricing rules
        subtotal = service_subtotal + add_ons_subtotal
        pricing_adjustments = []
        
        pricing_rules = await self.get_pricing_rules(location_id, service_type_id, check_in, check_out)
        
        for rule in pricing_rules:
            rule_type = rule.get('rule_type')
            
            if rule_type == 'blackout':
                # Blackouts don't affect price, just block dates
                continue
            
            multiplier = rule.get('multiplier', 1.0)
            flat_adjustment = rule.get('flat_adjustment', 0.0)
            
            if rule_type == 'weekend':
                # Count weekend days
                weekend_days = 0
                current = check_in
                days_of_week = rule.get('days_of_week', [5, 6])  # Default Sat/Sun
                while current < check_out:
                    if current.weekday() in days_of_week:
                        weekend_days += 1
                    current += timedelta(days=1)
                
                if weekend_days > 0:
                    # Apply weekend multiplier only to weekend portion
                    weekend_ratio = weekend_days / nights
                    adjustment = (subtotal * weekend_ratio) * (multiplier - 1)
                    subtotal += adjustment
                    pricing_adjustments.append({
                        "rule_id": rule['id'],
                        "rule_name": rule.get('name', 'Weekend'),
                        "rule_type": rule_type,
                        "adjustment": adjustment,
                        "description": f"{weekend_days} weekend day(s), {int((multiplier-1)*100)}% surcharge"
                    })
            else:
                # Holiday/seasonal - apply to full amount
                if multiplier != 1.0:
                    adjustment = subtotal * (multiplier - 1)
                    subtotal += adjustment
                    pricing_adjustments.append({
                        "rule_id": rule['id'],
                        "rule_name": rule.get('name'),
                        "rule_type": rule_type,
                        "adjustment": adjustment,
                        "description": f"{int((multiplier-1)*100)}% {'surcharge' if multiplier > 1 else 'discount'}"
                    })
                
                if flat_adjustment != 0:
                    subtotal += flat_adjustment
                    pricing_adjustments.append({
                        "rule_id": rule['id'],
                        "rule_name": rule.get('name'),
                        "rule_type": rule_type,
                        "adjustment": flat_adjustment,
                        "description": f"${abs(flat_adjustment):.2f} {'fee' if flat_adjustment > 0 else 'discount'}"
                    })
        
        # Promo code (placeholder for future)
        discount_amount = 0.0
        if promo_code:
            # TODO: Implement promo code lookup
            pass
        
        # Tax
        tax_rate = await self.get_system_setting('tax_rate', DEFAULT_TAX_RATE)
        tax_amount = subtotal * (tax_rate / 100)
        
        # Total
        total = subtotal + tax_amount - discount_amount
        
        # Deposit calculation
        deposit_percentage = await self.get_system_setting('deposit_percentage', DEFAULT_DEPOSIT_PERCENTAGE)
        deposit_amount = round(total * (deposit_percentage / 100), 2)
        balance_due = round(total - deposit_amount, 2)
        
        # Check capacity
        is_available, requires_approval, available_spots = await self.check_capacity(
            location_id, check_in, check_out, accommodation_type, dog_count, exclude_booking_id
        )
        
        # Check blackout dates
        blocked_dates = await self.check_blackout_dates(location_id, check_in, check_out)
        
        warnings = []
        if requires_approval:
            warnings.append(f"This booking exceeds normal capacity ({available_spots} spots available). It will require staff approval.")
        if blocked_dates:
            warnings.append(f"Warning: Your dates include {len(blocked_dates)} blackout date(s). Booking may be subject to additional review.")
        
        return {
            "base_price": base_price,
            "nights": nights,
            "dog_count": dog_count,
            "service_subtotal": round(service_subtotal, 2),
            "add_ons_subtotal": round(add_ons_subtotal, 2),
            "add_ons_detail": add_ons_detail,
            "pricing_adjustments": pricing_adjustments,
            "subtotal": round(subtotal, 2),
            "tax_rate": tax_rate,
            "tax_amount": round(tax_amount, 2),
            "discount_amount": round(discount_amount, 2),
            "total": round(total, 2),
            "deposit_percentage": deposit_percentage,
            "deposit_amount": deposit_amount,
            "balance_due": balance_due,
            "is_over_capacity": requires_approval,
            "requires_approval": requires_approval or len(blocked_dates) > 0,
            "blocked_dates": blocked_dates,
            "warnings": warnings
        }
    
    async def get_cancellation_policy(self, booking: Dict) -> Optional[Dict]:
        """Get applicable cancellation policy for a booking"""
        service_type_id = booking.get('service_type_id')
        location_id = booking.get('location_id')
        
        query = {"active": True}
        policies = await self.db.cancellation_policies.find(query, {"_id": 0}).sort("days_before_checkin", -1).to_list(100)
        
        for policy in policies:
            # Check location
            if policy.get('location_id') and policy['location_id'] != location_id:
                continue
            
            # Check service type
            if policy.get('service_type_ids') and service_type_id not in policy.get('service_type_ids', []):
                continue
            
            return policy
        
        # Default policy
        return {
            "name": "Default Policy",
            "days_before_checkin": 7,
            "refund_percentage": 100,
            "refund_deposit_only": False
        }
    
    async def calculate_refund(self, booking: Dict, cancellation_date: datetime = None) -> Dict[str, Any]:
        """
        Calculate refund amount based on hours-based cancellation policy.
        
        AUTHORITATIVE REFUND POLICY (hours-based):
        - ≥ 48 hours before check-in: 100% refund
        - ≥ 24 and < 48 hours before check-in: 50% refund
        - < 24 hours before check-in: 0% refund
        
        Cancellation is ALWAYS allowed, but refund varies based on timing.
        """
        cancellation_date = cancellation_date or datetime.now(timezone.utc)
        
        check_in = booking.get('check_in_date')
        if isinstance(check_in, str):
            # Assume 2pm (14:00) check-in time if only date is provided
            if 'T' not in check_in:
                check_in = f"{check_in}T14:00:00+00:00"
            check_in = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
        
        # Ensure cancellation_date is timezone-aware
        if cancellation_date.tzinfo is None:
            cancellation_date = cancellation_date.replace(tzinfo=timezone.utc)
        if check_in.tzinfo is None:
            check_in = check_in.replace(tzinfo=timezone.utc)
        
        # Calculate hours until check-in (CRITICAL: use total_seconds, NOT .days)
        time_diff = check_in - cancellation_date
        hours_until_checkin = time_diff.total_seconds() / 3600  # Convert seconds to hours
        
        # Get total amount (paid or owed)
        total_paid = 0.0
        if booking.get('deposit_paid'):
            total_paid += booking.get('deposit_amount', 0)
        if booking.get('balance_paid'):
            total_paid += booking.get('balance_due', 0)
        
        # If nothing paid yet, use total_price as the refund base
        total_amount = booking.get('total_price', 0) or booking.get('total', 0) or total_paid
        
        # Apply hours-based refund policy
        refund_percentage = 0.0
        policy_tier = 'no_refund'
        policy_description = 'Less than 24 hours before check-in - no refund'
        
        if hours_until_checkin >= 48:
            refund_percentage = 100.0
            policy_tier = 'full_refund'
            policy_description = '48+ hours before check-in - full refund'
        elif hours_until_checkin >= 24:
            refund_percentage = 50.0
            policy_tier = 'partial_refund'
            policy_description = '24-48 hours before check-in - 50% refund'
        
        # Calculate actual refund amount based on what was paid
        refund_amount = (total_paid * refund_percentage) / 100 if total_paid > 0 else (total_amount * refund_percentage) / 100
        
        return {
            "cancellation_allowed": True,  # Cancellation is ALWAYS allowed
            "total_paid": total_paid,
            "total_amount": total_amount,
            "refund_percentage": refund_percentage,
            "refund_amount": round(refund_amount, 2),
            "policy_tier": policy_tier,
            "policy_description": policy_description,
            "hours_until_checkin": round(hours_until_checkin, 1),
            # Deprecated fields for backwards compatibility
            "days_until_checkin": int(hours_until_checkin / 24),
            "policy_applied": policy_description,
        }

    def can_modify_booking(self, booking: Dict, current_time: datetime = None) -> Dict[str, Any]:
        """
        Check if a booking can be modified.
        
        Modification rules:
        - Status must not be completed, cancelled, checked_out, or no_show
        - Must be 24+ hours before check-in
        
        Returns eligibility result with reason if not allowed.
        """
        current_time = current_time or datetime.now(timezone.utc)
        
        status = (booking.get('status') or '').lower()
        non_modifiable = ['completed', 'cancelled', 'checked_out', 'no_show']
        
        if status in non_modifiable:
            return {
                'allowed': False,
                'reason': f'Cannot modify booking with status: {status}'
            }
        
        check_in = booking.get('check_in_date')
        if isinstance(check_in, str):
            if 'T' not in check_in:
                check_in = f"{check_in}T14:00:00+00:00"
            check_in = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
        
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        if check_in.tzinfo is None:
            check_in = check_in.replace(tzinfo=timezone.utc)
        
        time_diff = check_in - current_time
        hours_until_checkin = time_diff.total_seconds() / 3600
        
        if hours_until_checkin < 24:
            return {
                'allowed': False,
                'reason': 'Cannot modify booking within 24 hours of check-in',
                'hours_until_checkin': round(hours_until_checkin, 1)
            }
        
        return {
            'allowed': True,
            'reason': None,
            'hours_until_checkin': round(hours_until_checkin, 1)
        }

