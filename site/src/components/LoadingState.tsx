export function LoadingState({ label = 'Carregando dados públicos…' }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <span className="loading-state__line" />
      <span>{label}</span>
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="error-state" role="alert">
      <strong>Não foi possível carregar esta visualização.</strong>
      <span>{message}</span>
    </div>
  )
}
