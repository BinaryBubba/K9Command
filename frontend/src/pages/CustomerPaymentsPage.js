import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { ArrowLeftIcon, CreditCardIcon, WalletIcon } from 'lucide-react';
import { dataClient, dataMode } from '../data/client';

const CustomerPaymentsPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [invoices, setInvoices] = useState([]);
  const [payMode, setPayMode] = useState('square'); // 'square' | 'crypto'
  const [payingId, setPayingId] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const list = await dataClient.listInvoices();
        if (!mounted) return;
        setInvoices(list || []);
      } catch {
        toast.error('Failed to load invoices');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const unpaid = useMemo(() => (invoices || []).filter((i) => i.status !== 'paid'), [invoices]);

  const handlePay = async (invoiceId) => {
    if (payMode === 'crypto') {
      toast.message('Crypto payments are coming soon (USDC / stablecoins).');
      return;
    }
    try {
      setPayingId(invoiceId);
      const paid = await dataClient.payInvoice(invoiceId, { provider: 'square', method: 'card' });
      setInvoices((prev) => prev.map((i) => (i.id === invoiceId ? paid : i)));
      toast.success('Payment successful');
    } catch {
      toast.error('Payment failed');
    } finally {
      setPayingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/50 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => navigate('/customer/dashboard')}>
              <ArrowLeftIcon className="mr-2" size={18} />
              Back
            </Button>
            <div className="flex items-center gap-2">
              <CreditCardIcon size={20} />
              <h1 className="text-xl font-serif font-bold text-primary">Payments</h1>
            </div>
          </div>

          <div className="text-xs text-muted-foreground hidden sm:block">
            Data mode: <span className="font-medium">{dataMode}</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader>
              <CardTitle className="font-serif">Pay with</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                className="w-full justify-start"
                variant={payMode === 'square' ? 'default' : 'outline'}
                onClick={() => setPayMode('square')}
              >
                <CreditCardIcon className="mr-2" size={18} />
                Square (Card)
              </Button>
              <Button
                className="w-full justify-start"
                variant={payMode === 'crypto' ? 'default' : 'outline'}
                onClick={() => setPayMode('crypto')}
              >
                <WalletIcon className="mr-2" size={18} />
                Crypto (Coming soon)
              </Button>
              <div className="text-xs text-muted-foreground">
                Square can go live first. Crypto can be added later (USDC recommended).
              </div>
            </CardContent>
          </Card>

          <div className="lg:col-span-2 space-y-6">
            <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader>
                <CardTitle className="font-serif">Unpaid invoices</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="text-muted-foreground">Loading…</div>
                ) : unpaid.length ? (
                  <div className="space-y-3">
                    {unpaid.map((inv) => (
                      <div key={inv.id} className="p-4 rounded-xl border border-border/50 bg-muted/30">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <div className="font-medium">
                              Invoice {inv.id.slice(-6).toUpperCase()}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              Amount: ${Number(inv.amount || 0).toFixed(2)} • Status: {inv.status}
                            </div>
                          </div>
                          <Button
                            onClick={() => handlePay(inv.id)}
                            disabled={payingId === inv.id}
                          >
                            {payingId === inv.id ? 'Processing…' : 'Pay now'}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted-foreground">No unpaid invoices.</div>
                )}
              </CardContent>
            </Card>

            <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader>
                <CardTitle className="font-serif">Payment history</CardTitle>
              </CardHeader>
              <CardContent>
                {!loading && invoices.length ? (
                  <div className="space-y-2">
                    {invoices.map((inv) => (
                      <div key={inv.id} className="flex items-center justify-between text-sm p-3 rounded-lg border border-border/50">
                        <div className="flex flex-col">
                          <span className="font-medium">Invoice {inv.id.slice(-6).toUpperCase()}</span>
                          <span className="text-muted-foreground">
                            ${Number(inv.amount || 0).toFixed(2)} • {inv.provider || 'square'} • {inv.status}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {inv.paidAt ? `Paid ${new Date(inv.paidAt).toLocaleString()}` : `Created ${new Date(inv.createdAt).toLocaleString()}`}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : loading ? (
                  <div className="text-muted-foreground">Loading…</div>
                ) : (
                  <div className="text-muted-foreground">
                    No history yet. Create a booking to generate an invoice.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};

export default CustomerPaymentsPage;
