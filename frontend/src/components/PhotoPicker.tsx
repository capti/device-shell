/** Выбор фотографий в модальных окнах: несколько файлов и остаток лимита. */

import { Badge, Button, CloseButton, FileButton, Group, Stack, Text } from '@mantine/core'

interface PhotoPickerProps {
  files: File[]
  maxFiles: number
  onChange: (files: File[]) => void
  disabled?: boolean
}

function normalize(payload: File | File[] | null): File[] {
  if (payload === null) return []
  return Array.isArray(payload) ? payload : [payload]
}

export function PhotoPicker({
  files,
  maxFiles,
  onChange,
  disabled = false,
}: PhotoPickerProps) {
  const limitReached = files.length >= maxFiles

  const add = (payload: File | File[] | null) => {
    const picked = normalize(payload)
    onChange([...files, ...picked].slice(0, maxFiles))
  }

  const remove = (index: number) => {
    onChange(files.filter((_, position) => position !== index))
  }

  return (
    <Stack gap={4}>
      <Group justify="space-between" align="center">
        <Text size="sm">Фотографии</Text>
        <Text size="xs" c="dimmed">
          {files.length} из {maxFiles}
        </Text>
      </Group>
      <FileButton
        onChange={add}
        accept="image/jpeg,image/png,image/webp"
        multiple
        disabled={disabled || limitReached}
      >
        {(props) => (
          <Button {...props} size="xs" variant="default" disabled={disabled || limitReached}>
            Приложить фото
          </Button>
        )}
      </FileButton>
      {maxFiles === 0 && (
        <Text size="xs" c="dimmed">
          Лимит фотографий на устройство уже исчерпан.
        </Text>
      )}
      {files.map((file, index) => (
        <Group key={`${file.name}-${index}`} gap="xs" justify="space-between" wrap="nowrap">
          <Badge variant="light" size="sm" style={{ textTransform: 'none' }}>
            {file.name}
          </Badge>
          <CloseButton
            size="sm"
            aria-label={`Убрать ${file.name}`}
            onClick={() => remove(index)}
          />
        </Group>
      ))}
    </Stack>
  )
}
