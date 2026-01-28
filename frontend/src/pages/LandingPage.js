import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { DogIcon, CalendarIcon, ImageIcon, StarIcon } from 'lucide-react';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative h-screen flex items-center justify-center">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: "url('https://images.unsplash.com/photo-1560829571-6e9583e4a71a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDN8MHwxfHNlYXJjaHwxfHxoYXBweSUyMGRvZyUyMHBsYXlpbmclMjBncmFzc3xlbnwwfHx8fDE3Njk2MTk2NjV8MA&ixlib=rb-4.1.0&q=85')",
          }}
        >
          <div className="hero-overlay absolute inset-0"></div>
        </div>
        
        <div className="relative z-10 text-center text-white px-4 max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-7xl font-serif font-bold tracking-tight leading-tight mb-6">
            A Home Away From Home
          </h1>
          <p className="text-xl md:text-2xl font-sans mb-8 leading-relaxed opacity-95">
            Premium boarding with daily photo updates, AI-powered summaries, and care that feels like family.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Button
              data-testid="hero-book-now-button"
              onClick={() => navigate('/auth')}
              className="rounded-full px-8 py-6 text-lg font-semibold bg-secondary hover:bg-secondary/90 text-secondary-foreground shadow-xl hover:shadow-2xl hover:-translate-y-1 transition-all duration-300"
            >
              Book Your Stay
            </Button>
            <Button
              data-testid="hero-learn-more-button"
              onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })}
              variant="outline"
              className="rounded-full px-8 py-6 text-lg font-semibold border-2 border-white bg-white/10 backdrop-blur-sm hover:bg-white/20 text-white"
            >
              Learn More
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-4 md:px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-serif font-semibold text-primary mb-4">
              Why Families Trust Us
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              We combine professional care with modern technology to keep you connected with your furry family members.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div data-testid="feature-card-updates" className="bg-white rounded-2xl border border-border/50 shadow-sm hover:shadow-lg transition-all duration-300 p-8 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 text-primary mb-4">
                <ImageIcon size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold mb-2">Daily Photo Updates</h3>
              <p className="text-muted-foreground">
                Receive personalized photo updates every afternoon, so you never miss a moment.
              </p>
            </div>

            <div data-testid="feature-card-ai" className="bg-white rounded-2xl border border-border/50 shadow-sm hover:shadow-lg transition-all duration-300 p-8 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-secondary/20 text-secondary-foreground mb-4">
                <StarIcon size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold mb-2">AI-Powered Summaries</h3>
              <p className="text-muted-foreground">
                Get warm, personalized daily summaries written just for you and your pup.
              </p>
            </div>

            <div data-testid="feature-card-booking" className="bg-white rounded-2xl border border-border/50 shadow-sm hover:shadow-lg transition-all duration-300 p-8 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 text-primary mb-4">
                <CalendarIcon size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold mb-2">Easy Booking</h3>
              <p className="text-muted-foreground">
                Book stays, manage profiles, and track your visits all in one place.
              </p>
            </div>

            <div data-testid="feature-card-care" className="bg-white rounded-2xl border border-border/50 shadow-sm hover:shadow-lg transition-all duration-300 p-8 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-secondary/20 text-secondary-foreground mb-4">
                <DogIcon size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold mb-2">Expert Care</h3>
              <p className="text-muted-foreground">
                Our trained staff ensures every dog gets the love and attention they deserve.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-4 md:px-8 bg-primary text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-serif font-bold mb-6">
            Ready to Give Your Pup a Vacation?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join hundreds of happy dog families who trust us with their furry loved ones.
          </p>
          <Button
            data-testid="cta-get-started-button"
            onClick={() => navigate('/auth')}
            className="rounded-full px-10 py-6 text-lg font-semibold bg-secondary hover:bg-secondary/90 text-secondary-foreground shadow-xl hover:shadow-2xl hover:-translate-y-1 transition-all duration-300"
          >
            Get Started Today
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white py-12 px-4 border-t">
        <div className="max-w-7xl mx-auto text-center text-muted-foreground">
          <p className="mb-4">© 2025 Kennel Operations Platform. All rights reserved.</p>
          <div className="flex gap-6 justify-center">
            <Link to="/auth" className="hover:text-primary transition-colors">Login</Link>
            <span>•</span>
            <a href="#features" className="hover:text-primary transition-colors">Features</a>
            <span>•</span>
            <a href="mailto:hello@kennelops.com" className="hover:text-primary transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
