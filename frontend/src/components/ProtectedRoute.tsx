import React from 'react';
import { Navigate } from 'react-router-dom';
import { auth } from '../services/api';
import type { UserRole } from '../types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  roles?: UserRole[];
}

export function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  if (!auth.isLoggedIn()) {
    return <Navigate to="/login" replace />;
  }
  const user = auth.getUser();
  if (roles && user && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
