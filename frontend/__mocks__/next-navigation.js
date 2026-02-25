export const useRouter = () => ({
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
  back: jest.fn(),
});

export const useParams = () => ({});
export const usePathname = () => "/";
export const useSearchParams = () => new URLSearchParams();