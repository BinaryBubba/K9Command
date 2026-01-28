import React from 'react';
import AuthForm from '../components/AuthForm';

const AuthPage = () => {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-gradient-to-br from-primary/5 via-background to-secondary/5">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-8 border border-border/50">
        <AuthForm />
      </div>
    </div>
  );
};

export default AuthPage;
