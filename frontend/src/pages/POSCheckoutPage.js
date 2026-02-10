import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  ArrowLeftIcon, ShoppingCartIcon, TrashIcon, PlusIcon, MinusIcon,
  SearchIcon, CreditCardIcon, BanknoteIcon, CheckCircleIcon,
  ReceiptIcon, UserIcon
} from 'lucide-react';
import api from '../utils/api';

export default function POSCheckoutPage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [showReceipt, setShowReceipt] = useState(false);
  const [lastTransaction, setLastTransaction] = useState(null);
  
  // Payment options
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [discountAmount, setDiscountAmount] = useState(0);
  const [customerSearch, setCustomerSearch] = useState('');

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await api.get('/moego/inventory/products?active_only=true');
      setProducts(res.data.products?.filter(p => p.quantity > 0) || []);
    } catch (error) {
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const addToCart = (product) => {
    const existing = cart.find(item => item.product_id === product.id);
    
    if (existing) {
      if (existing.quantity >= product.quantity) {
        toast.error(`Only ${product.quantity} available`);
        return;
      }
      setCart(cart.map(item =>
        item.product_id === product.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      setCart([...cart, {
        product_id: product.id,
        sku: product.sku,
        name: product.name,
        price_cents: product.price_cents,
        quantity: 1,
        max_quantity: product.quantity
      }]);
    }
  };

  const updateCartQuantity = (productId, delta) => {
    setCart(cart.map(item => {
      if (item.product_id === productId) {
        const newQty = item.quantity + delta;
        if (newQty <= 0) return null;
        if (newQty > item.max_quantity) {
          toast.error(`Only ${item.max_quantity} available`);
          return item;
        }
        return { ...item, quantity: newQty };
      }
      return item;
    }).filter(Boolean));
  };

  const removeFromCart = (productId) => {
    setCart(cart.filter(item => item.product_id !== productId));
  };

  const clearCart = () => {
    setCart([]);
    setDiscountAmount(0);
    setPaymentMethod('cash');
  };

  const calculateTotals = () => {
    const subtotal = cart.reduce((sum, item) => sum + (item.price_cents * item.quantity), 0);
    const discount = Math.min(discountAmount * 100, subtotal);
    const afterDiscount = subtotal - discount;
    const tax = Math.round(afterDiscount * 0.08);
    const total = afterDiscount + tax;
    
    return { subtotal, discount, tax, total };
  };

  const processTransaction = async () => {
    if (cart.length === 0) {
      toast.error('Cart is empty');
      return;
    }
    
    setProcessing(true);
    try {
      const items = cart.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity
      }));
      
      const res = await api.post('/moego/pos/transaction', {
        items,
        payment_method: paymentMethod,
        discount_cents: Math.round(discountAmount * 100)
      });
      
      setLastTransaction(res.data.transaction);
      setShowReceipt(true);
      toast.success('Transaction completed!');
      
      // Reload products to update quantities
      loadProducts();
      clearCart();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Transaction failed');
    } finally {
      setProcessing(false);
    }
  };

  const formatCurrency = (cents) => `$${(cents / 100).toFixed(2)}`;
  const totals = calculateTotals();

  const filteredProducts = products.filter(p =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.sku.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="pos-checkout-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/dashboard')} className="text-slate-400 hover:text-white">
              <ArrowLeftIcon size={20} />
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-white">POS Checkout</h1>
              <p className="text-slate-400 text-sm">Point of Sale</p>
            </div>
          </div>
          <Button variant="outline" onClick={() => navigate('/admin/inventory')} className="border-slate-600 text-slate-300">
            Manage Inventory
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-3 gap-6">
          {/* Products Grid - 2 columns */}
          <div className="col-span-2">
            {/* Search */}
            <div className="relative mb-4">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <Input
                placeholder="Search products by name or SKU..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-slate-800 border-slate-700 text-white"
              />
            </div>

            {/* Products */}
            <div className="grid grid-cols-3 gap-4 max-h-[calc(100vh-220px)] overflow-y-auto">
              {filteredProducts.length === 0 ? (
                <div className="col-span-3 text-center py-12 text-slate-500">
                  No products found
                </div>
              ) : (
                filteredProducts.map(product => (
                  <Card
                    key={product.id}
                    className="bg-slate-800 border-slate-700 cursor-pointer hover:bg-slate-750 hover:border-blue-500/50 transition-all"
                    onClick={() => addToCart(product)}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <Badge className="bg-slate-700 text-slate-300 text-xs">{product.sku}</Badge>
                        <span className="text-xs text-slate-500">{product.quantity} in stock</span>
                      </div>
                      <h3 className="text-white font-medium mb-1 line-clamp-2">{product.name}</h3>
                      <p className="text-lg font-bold text-green-400">{formatCurrency(product.price_cents)}</p>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>

          {/* Cart - 1 column */}
          <div>
            <Card className="bg-slate-900 border-slate-700 sticky top-4">
              <CardHeader className="border-b border-slate-700 pb-4">
                <CardTitle className="text-white flex items-center gap-2">
                  <ShoppingCartIcon size={20} />
                  Cart ({cart.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                {cart.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <ShoppingCartIcon className="mx-auto mb-2" size={32} />
                    <p>Cart is empty</p>
                    <p className="text-xs">Click products to add</p>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-64 overflow-y-auto mb-4">
                    {cart.map(item => (
                      <div key={item.product_id} className="flex items-center gap-3 bg-slate-800 rounded-lg p-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-white text-sm font-medium truncate">{item.name}</p>
                          <p className="text-slate-400 text-xs">{formatCurrency(item.price_cents)} each</p>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => updateCartQuantity(item.product_id, -1)}
                            className="h-7 w-7 p-0 text-slate-400"
                          >
                            <MinusIcon size={14} />
                          </Button>
                          <span className="text-white w-6 text-center">{item.quantity}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => updateCartQuantity(item.product_id, 1)}
                            className="h-7 w-7 p-0 text-slate-400"
                          >
                            <PlusIcon size={14} />
                          </Button>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFromCart(item.product_id)}
                          className="h-7 w-7 p-0 text-red-400"
                        >
                          <TrashIcon size={14} />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Discount */}
                <div className="mb-4">
                  <label className="text-xs text-slate-400 block mb-1">Discount ($)</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={discountAmount}
                    onChange={(e) => setDiscountAmount(parseFloat(e.target.value) || 0)}
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                </div>

                {/* Payment Method */}
                <div className="mb-4">
                  <label className="text-xs text-slate-400 block mb-1">Payment Method</label>
                  <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cash">
                        <span className="flex items-center gap-2">
                          <BanknoteIcon size={14} /> Cash
                        </span>
                      </SelectItem>
                      <SelectItem value="card">
                        <span className="flex items-center gap-2">
                          <CreditCardIcon size={14} /> Card
                        </span>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Totals */}
                <div className="border-t border-slate-700 pt-4 space-y-2">
                  <div className="flex justify-between text-slate-400">
                    <span>Subtotal</span>
                    <span>{formatCurrency(totals.subtotal)}</span>
                  </div>
                  {totals.discount > 0 && (
                    <div className="flex justify-between text-green-400">
                      <span>Discount</span>
                      <span>-{formatCurrency(totals.discount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-slate-400">
                    <span>Tax (8%)</span>
                    <span>{formatCurrency(totals.tax)}</span>
                  </div>
                  <div className="flex justify-between text-white text-xl font-bold pt-2 border-t border-slate-700">
                    <span>Total</span>
                    <span>{formatCurrency(totals.total)}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="mt-4 space-y-2">
                  <Button
                    onClick={processTransaction}
                    disabled={cart.length === 0 || processing}
                    className="w-full bg-green-600 hover:bg-green-700 py-6 text-lg"
                  >
                    {processing ? 'Processing...' : `Charge ${formatCurrency(totals.total)}`}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={clearCart}
                    disabled={cart.length === 0}
                    className="w-full border-slate-600 text-slate-300"
                  >
                    Clear Cart
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      {/* Receipt Modal */}
      {showReceipt && lastTransaction && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <Card className="bg-white w-80 text-black">
            <CardContent className="p-6">
              <div className="text-center mb-4">
                <CheckCircleIcon className="mx-auto text-green-500 mb-2" size={48} />
                <h3 className="font-bold text-xl">Transaction Complete</h3>
              </div>
              
              <div className="border-t border-b py-4 my-4 space-y-2">
                {lastTransaction.line_items?.map((item, i) => (
                  <div key={i} className="flex justify-between text-sm">
                    <span>{item.name} x{item.quantity}</span>
                    <span>{formatCurrency(item.line_total_cents)}</span>
                  </div>
                ))}
              </div>
              
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span>{formatCurrency(lastTransaction.subtotal_cents)}</span>
                </div>
                {lastTransaction.discount_cents > 0 && (
                  <div className="flex justify-between text-green-600">
                    <span>Discount</span>
                    <span>-{formatCurrency(lastTransaction.discount_cents)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Tax</span>
                  <span>{formatCurrency(lastTransaction.tax_cents)}</span>
                </div>
                <div className="flex justify-between font-bold text-lg pt-2 border-t">
                  <span>Total</span>
                  <span>{formatCurrency(lastTransaction.total_cents)}</span>
                </div>
              </div>
              
              <div className="text-center mt-4 text-xs text-slate-500">
                <p>Payment: {lastTransaction.payment_method}</p>
                <p>ID: {lastTransaction.id?.slice(0, 8)}</p>
              </div>
              
              <Button
                onClick={() => setShowReceipt(false)}
                className="w-full mt-4"
              >
                Done
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
