export default function authHeader(accessToken: string) {
  if (accessToken) {
    return { Authorization: 'Bearer ' + accessToken};
  } else {
    return {};
  }
}