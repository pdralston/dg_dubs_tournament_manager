import { createBrowserRouter } from 'react-router-dom';
import Shell from './shell/Shell';
import PlatformLanding from './landing/PlatformLanding';
import OrgLanding from './landing/OrgLanding';
import AppHost from './host/AppHost';

// URL hierarchy (org-first, matches the DG-Rater path scheme):
//   /                  platform landing + org directory (outside the shell)
//   /:org              org landing (apps directory)      ┐ wrapped in Shell
//   /:org/:app/*       mounted app (AppHost)             ┘ (header + switcher)
//
// The app route is a splat (/*) so each ported app can own its own sub-routes
// internally (e.g. /svdgc/putt/tournament/42). basename stays '/' during the
// interim; it moves with `base` if a sub-path deploy is ever chosen.
export const router = createBrowserRouter([
  {
    path: '/',
    element: <PlatformLanding />,
  },
  {
    element: <Shell />,
    children: [
      { path: '/:org', element: <OrgLanding /> },
      { path: '/:org/:app/*', element: <AppHost /> },
    ],
  },
]);
