import React, { useEffect } from 'react';
import { AppState, Auth0Provider, useAuth0 } from '@auth0/auth0-react';
import { useNavigate } from 'react-router';

// Auth0Provider must wrap the tree whenever child components call useAuth0(),
// even when VITE_SKIP_AUTH=true (local Neo4j Desktop workflow).
const domain = import.meta.env.VITE_AUTH0_DOMAIN || 'local-dev-placeholder.us.auth0.com';
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID || 'local-dev-placeholder-client-id';
const Auth0ProviderWithHistory: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();

  function onRedirectCallback(appState?: AppState) {
    localStorage.removeItem('isReadOnlyMode');
    navigate(appState?.returnTo || window.location.pathname, { state: appState });
  }

  return (
    <Auth0Provider
      domain={domain as string}
      clientId={clientId as string}
      authorizationParams={{ redirect_uri: window.location.origin }}
      onRedirectCallback={onRedirectCallback}
    >
      {children}
    </Auth0Provider>
  );
};

export const AuthenticationGuard: React.FC<{ component: React.ComponentType<object> }> = ({ component }) => {
  const { isAuthenticated, isLoading } = useAuth0();
  const Component = component;
  const navigate = useNavigate();
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      localStorage.setItem('isReadOnlyMode', 'true');
      navigate('/readonly', { replace: true });
    }
  }, [isLoading, isAuthenticated]);
  return <Component />;
};

export default Auth0ProviderWithHistory;
