import { Link as RouterLink } from "react-router-dom";
import { Flex, Button, Box } from "@chakra-ui/react";


function Navigation() {
  return (
    <Box bg="gray.100" px={4} py={3} boxShadow="md">
      <Flex as="nav" gap={4} align="center">
        <Button as={RouterLink} to="/" colorScheme="teal" variant="ghost">
          首頁
        </Button>
        <Button as={RouterLink} to="/dashboard" colorScheme="teal" variant="ghost">
          圖表頁
        </Button>
        <Button as={RouterLink} to="/sessionmanager" colorScheme="teal" variant="ghost">
          Session 管理
        </Button>
      </Flex>
    </Box>
  );
}

export default Navigation