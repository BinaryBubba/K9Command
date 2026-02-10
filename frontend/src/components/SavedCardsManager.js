import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { toast } from 'sonner';
import { 
  CreditCardIcon, 
  PlusIcon, 
  TrashIcon, 
  Loader2Icon,
  ShieldCheckIcon,
  AlertCircleIcon
} from 'lucide-react';
import api from '../utils/api';

const CARD_BRAND_COLORS = {
  'VISA': 'bg-blue-500',
  'MASTERCARD': 'bg-red-500',
  'AMERICAN_EXPRESS': 'bg-green-600',
  'DISCOVER': 'bg-orange-500',
  'DEFAULT': 'bg-slate-500'
};

const SavedCardsManager = ({ onCardSelect, selectedCardId, showAddOnly = false }) => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddCard, setShowAddCard] = useState(false);
  const [addingCard, setAddingCard] = useState(false);
  const [paymentConfig, setPaymentConfig] = useState(null);
  
  // Form state for adding card (mock mode)
  const [cardNumber, setCardNumber] = useState('');
  const [expMonth, setExpMonth] = useState('');
  const [expYear, setExpYear] = useState('');
  const [cvv, setCvv] = useState('');
  const [postalCode, setPostalCode] = useState('');

  useEffect(() => {
    loadCards();
    loadPaymentConfig();
  }, []);

  const loadPaymentConfig = async () => {
    try {
      const res = await api.get('/moego/payments/config');
      setPaymentConfig(res.data);
    } catch (error) {
      console.error('Failed to load payment config:', error);
    }
  };

  const loadCards = async () => {
    setLoading(true);
    try {
      const res = await api.get('/moego/payments/cards');
      setCards(res.data.cards || []);
      
      // Auto-select first card if none selected
      if (res.data.cards?.length > 0 && !selectedCardId && onCardSelect) {
        onCardSelect(res.data.cards[0].card_id);
      }
    } catch (error) {
      console.error('Failed to load cards:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCard = async () => {
    if (!cardNumber || !expMonth || !expYear) {
      toast.error('Please fill in all card details');
      return;
    }
    
    setAddingCard(true);
    try {
      // In mock mode, we simulate tokenization
      // In production with Square, use Square Web Payments SDK
      await api.post('/moego/payments/cards', {
        source_id: `mock_token_${Date.now()}`,
        cardholder_name: 'Card Holder',
        postal_code: postalCode
      });
      
      toast.success('Card added successfully');
      setShowAddCard(false);
      resetForm();
      loadCards();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add card');
    } finally {
      setAddingCard(false);
    }
  };

  const handleDeleteCard = async (cardId) => {
    try {
      await api.delete(`/moego/payments/cards/${cardId}`);
      toast.success('Card removed');
      loadCards();
    } catch (error) {
      toast.error('Failed to remove card');
    }
  };

  const resetForm = () => {
    setCardNumber('');
    setExpMonth('');
    setExpYear('');
    setCvv('');
    setPostalCode('');
  };

  const formatCardNumber = (value) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = (matches && matches[0]) || '';
    const parts = [];
    for (let i = 0, len = match.length; i < len; i += 4) {
      parts.push(match.substring(i, i + 4));
    }
    return parts.length ? parts.join(' ') : value;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2Icon className="animate-spin text-primary" size={24} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Mock Mode Notice */}
      {paymentConfig?.mock_mode && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
          <AlertCircleIcon className="text-amber-500 flex-shrink-0 mt-0.5" size={18} />
          <div>
            <p className="text-sm text-amber-800 font-medium">Test Mode</p>
            <p className="text-xs text-amber-700">Payments are simulated. No real charges will be made.</p>
          </div>
        </div>
      )}

      {/* Card List */}
      {!showAddOnly && cards.length > 0 && (
        <div className="space-y-3">
          {cards.map(card => (
            <div 
              key={card.card_id}
              className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                selectedCardId === card.card_id 
                  ? 'border-primary bg-primary/5' 
                  : 'border-border hover:border-primary/50'
              }`}
              onClick={() => onCardSelect && onCardSelect(card.card_id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg ${CARD_BRAND_COLORS[card.card_brand] || CARD_BRAND_COLORS.DEFAULT} flex items-center justify-center`}>
                    <CreditCardIcon className="text-white" size={20} />
                  </div>
                  <div>
                    <p className="font-medium">{card.card_brand} •••• {card.last_4}</p>
                    <p className="text-sm text-muted-foreground">
                      Expires {card.exp_month}/{card.exp_year}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {selectedCardId === card.card_id && (
                    <Badge className="bg-primary text-white">Selected</Badge>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteCard(card.card_id);
                    }}
                    className="text-muted-foreground hover:text-red-500"
                  >
                    <TrashIcon size={16} />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No Cards Message */}
      {!showAddOnly && cards.length === 0 && (
        <div className="text-center py-8 bg-slate-50 rounded-xl">
          <CreditCardIcon className="mx-auto text-slate-300 mb-3" size={48} />
          <p className="text-muted-foreground mb-4">No payment methods saved</p>
        </div>
      )}

      {/* Add Card Button */}
      <Button
        onClick={() => setShowAddCard(true)}
        variant={cards.length === 0 ? "default" : "outline"}
        className="w-full"
        data-testid="add-card-btn"
      >
        <PlusIcon size={16} className="mr-2" />
        Add Payment Method
      </Button>

      {/* Add Card Dialog */}
      <Dialog open={showAddCard} onOpenChange={setShowAddCard}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CreditCardIcon size={20} />
              Add Payment Method
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Security Notice */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground bg-slate-50 p-3 rounded-lg">
              <ShieldCheckIcon size={16} className="text-green-600" />
              <span>Your card information is encrypted and secure</span>
            </div>

            {/* Card Number */}
            <div>
              <Label htmlFor="card-number">Card Number</Label>
              <Input
                id="card-number"
                placeholder="4111 1111 1111 1111"
                value={cardNumber}
                onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                maxLength={19}
                className="mt-1"
                data-testid="card-number-input"
              />
            </div>

            {/* Expiry & CVV */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label htmlFor="exp-month">Month</Label>
                <Input
                  id="exp-month"
                  placeholder="MM"
                  value={expMonth}
                  onChange={(e) => setExpMonth(e.target.value.replace(/\D/g, '').slice(0, 2))}
                  maxLength={2}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="exp-year">Year</Label>
                <Input
                  id="exp-year"
                  placeholder="YY"
                  value={expYear}
                  onChange={(e) => setExpYear(e.target.value.replace(/\D/g, '').slice(0, 2))}
                  maxLength={2}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="cvv">CVV</Label>
                <Input
                  id="cvv"
                  placeholder="123"
                  type="password"
                  value={cvv}
                  onChange={(e) => setCvv(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  maxLength={4}
                  className="mt-1"
                />
              </div>
            </div>

            {/* Postal Code */}
            <div>
              <Label htmlFor="postal">Billing Postal Code</Label>
              <Input
                id="postal"
                placeholder="12345"
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                maxLength={10}
                className="mt-1"
              />
            </div>

            {/* Test Card Hint */}
            {paymentConfig?.mock_mode && (
              <div className="text-xs text-muted-foreground bg-slate-50 p-2 rounded">
                <strong>Test card:</strong> 4111 1111 1111 1111, any future date, any CVV
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddCard(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddCard} disabled={addingCard}>
              {addingCard ? (
                <>
                  <Loader2Icon size={16} className="mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                'Add Card'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SavedCardsManager;
